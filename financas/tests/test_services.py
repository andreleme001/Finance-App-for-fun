"""Testes da camada de serviços com banco em memória."""

from datetime import date
from decimal import Decimal

import pytest

from models import (
    Categoria,
    Conta,
    Frequencia,
    Moeda,
    Prioridade,
    StatusTransacao,
    TipoCategoria,
    Transacao,
)
from repositories import (
    CategoriaRepository,
    ContaRepository,
    TransacaoRepository,
    inicializar,
)
from services import (
    ErroValidacao,
    LancamentoService,
    ParametroService,
    RelatorioService,
)

# IDs do seed: categorias 1=Salário Líquido (ENTRADA), 6=Aluguel (SAIDA),
# 10=Alimentação/Mercado (SAIDA); contas 1=Conta Corrente EUR,
# 2=Conta Corrente BRL.
CAT_SALARIO, CAT_ALUGUEL, CAT_MERCADO = 1, 6, 10
CONTA_EUR, CONTA_BRL = 1, 2


@pytest.fixture
def ambiente():
    conexao = inicializar(":memory:")
    transacao_repo = TransacaoRepository(conexao)
    categoria_repo = CategoriaRepository(conexao)
    conta_repo = ContaRepository(conexao)
    yield {
        "lancamentos": LancamentoService(
            transacao_repo, categoria_repo, conta_repo
        ),
        "relatorios": RelatorioService(
            transacao_repo, categoria_repo, conta_repo
        ),
        "parametros": ParametroService(categoria_repo, conta_repo),
        "categorias": categoria_repo,
        "contas": conta_repo,
        "transacoes": transacao_repo,
    }
    conexao.close()


def transacao(**ajustes) -> Transacao:
    base = dict(
        data=date(2026, 7, 15),
        descricao="Lançamento de teste",
        valor=Decimal("100.00"),
        categoria_id=CAT_MERCADO,
        conta_id=CONTA_EUR,
        status=StatusTransacao.REALIZADO,
    )
    base.update(ajustes)
    return Transacao(**base)


# ------------------------------------------------------------- lançamentos


def test_registrar_persiste(ambiente):
    criada = ambiente["lancamentos"].registrar(transacao())
    assert criada.id is not None


def test_registrar_rejeita_valor_nao_positivo(ambiente):
    with pytest.raises(ErroValidacao):
        ambiente["lancamentos"].registrar(transacao(valor=Decimal("0")))


def test_registrar_rejeita_categoria_inexistente(ambiente):
    with pytest.raises(ErroValidacao):
        ambiente["lancamentos"].registrar(transacao(categoria_id=999))


def test_registrar_rejeita_categoria_inativa(ambiente):
    categoria = ambiente["categorias"].buscar_por_id(CAT_MERCADO)
    categoria.ativa = False
    ambiente["categorias"].atualizar(categoria)
    with pytest.raises(ErroValidacao):
        ambiente["lancamentos"].registrar(transacao())


def test_registrar_rejeita_conta_inativa(ambiente):
    conta = ambiente["contas"].buscar_por_id(CONTA_EUR)
    conta.ativa = False
    ambiente["contas"].atualizar(conta)
    with pytest.raises(ErroValidacao):
        ambiente["lancamentos"].registrar(transacao())


def test_confirmar_previsto_com_ajustes(ambiente):
    prevista = ambiente["lancamentos"].registrar(
        transacao(status=StatusTransacao.PREVISTO, valor=Decimal("500.00"))
    )
    confirmada = ambiente["lancamentos"].confirmar(
        prevista.id, valor_real=Decimal("480.00"), data_real=date(2026, 7, 20)
    )
    assert confirmada.status is StatusTransacao.REALIZADO
    assert confirmada.valor == Decimal("480.00")
    assert confirmada.data == date(2026, 7, 20)
    persistida = ambiente["transacoes"].buscar_por_id(prevista.id)
    assert persistida.status is StatusTransacao.REALIZADO


def test_confirmar_rejeita_ja_realizada(ambiente):
    realizada = ambiente["lancamentos"].registrar(transacao())
    with pytest.raises(ErroValidacao):
        ambiente["lancamentos"].confirmar(realizada.id)


def test_criar_recorrente_gera_previstas(ambiente):
    meses = [date(2026, m, 5) for m in range(1, 13)]
    criadas = ambiente["lancamentos"].criar_recorrente(
        transacao(categoria_id=CAT_ALUGUEL, valor=Decimal("900.00")), meses
    )
    assert len(criadas) == 12
    assert all(t.status is StatusTransacao.PREVISTO for t in criadas)
    assert {t.data.month for t in criadas} == set(range(1, 13))
    assert (
        len(ambiente["transacoes"].listar(status=StatusTransacao.PREVISTO))
        == 12
    )


def test_remover(ambiente):
    criada = ambiente["lancamentos"].registrar(transacao())
    ambiente["lancamentos"].remover(criada.id)
    assert ambiente["transacoes"].buscar_por_id(criada.id) is None


# --------------------------------------------------------------- relatórios


def test_resumo_mensal_separa_status_e_moedas(ambiente):
    lanc = ambiente["lancamentos"]
    # Junho (mês anterior, entra só no acumulado): +1000 EUR realizado.
    lanc.registrar(
        transacao(
            data=date(2026, 6, 1),
            categoria_id=CAT_SALARIO,
            valor=Decimal("1000.00"),
        )
    )
    # Julho EUR: entrada 2000 realizada, saída 300 realizada, 200 prevista.
    lanc.registrar(
        transacao(
            data=date(2026, 7, 1),
            categoria_id=CAT_SALARIO,
            valor=Decimal("2000.00"),
        )
    )
    lanc.registrar(transacao(data=date(2026, 7, 5), valor=Decimal("300.00")))
    lanc.registrar(
        transacao(
            data=date(2026, 7, 25),
            valor=Decimal("200.00"),
            status=StatusTransacao.PREVISTO,
        )
    )
    # Julho BRL: saída 50 realizada.
    lanc.registrar(
        transacao(
            data=date(2026, 7, 8), conta_id=CONTA_BRL, valor=Decimal("50.00")
        )
    )
    # Agosto (fora do mês e do acumulado de julho).
    lanc.registrar(transacao(data=date(2026, 8, 1), valor=Decimal("999.00")))

    resumo = ambiente["relatorios"].resumo_mensal(date(2026, 7, 1))
    por_moeda = {b.moeda: b for b in resumo.moedas}
    assert set(por_moeda) == {Moeda.EUR, Moeda.BRL}

    eur = por_moeda[Moeda.EUR]
    assert eur.entradas_realizado == Decimal("2000.00")
    assert eur.saidas_realizado == Decimal("300.00")
    assert eur.saidas_previsto == Decimal("200.00")
    assert eur.saldo_realizado == Decimal("1700.00")
    assert eur.saldo_acumulado_realizado == Decimal("2700.00")
    assert eur.saldo_acumulado_previsto == Decimal("-200.00")

    brl = por_moeda[Moeda.BRL]
    assert brl.saidas_realizado == Decimal("50.00")
    assert brl.entradas_realizado == Decimal("0")


def test_comparativo_por_categoria_com_orcamento(ambiente):
    categoria = ambiente["categorias"].buscar_por_id(CAT_MERCADO)
    categoria.orcado_mensal = Decimal("400.00")
    ambiente["categorias"].atualizar(categoria)

    lanc = ambiente["lancamentos"]
    lanc.registrar(transacao(valor=Decimal("300.00")))
    lanc.registrar(
        transacao(valor=Decimal("150.00"), status=StatusTransacao.PREVISTO)
    )

    comparativo = ambiente["relatorios"].comparativo_por_categoria(
        date(2026, 7, 1)
    )
    assert len(comparativo) == 1
    linha = comparativo[0]
    assert linha.categoria_id == CAT_MERCADO
    assert linha.orcado == Decimal("400.00")
    assert linha.realizado == Decimal("300.00")
    assert linha.previsto == Decimal("150.00")
    assert linha.diferenca == Decimal("100.00")
    assert linha.percentual_utilizado == Decimal("75.0")


def test_comparativo_percentual_none_sem_orcamento(ambiente):
    ambiente["lancamentos"].registrar(transacao(valor=Decimal("300.00")))
    linha = ambiente["relatorios"].comparativo_por_categoria(date(2026, 7, 1))[
        0
    ]
    assert linha.percentual_utilizado is None
    assert linha.diferenca == Decimal("-300.00")


def test_evolucao_mensal_com_taxa_poupanca(ambiente):
    lanc = ambiente["lancamentos"]
    for mes in (6, 7):
        lanc.registrar(
            transacao(
                data=date(2026, mes, 1),
                categoria_id=CAT_SALARIO,
                valor=Decimal("1000.00"),
            )
        )
        lanc.registrar(
            transacao(data=date(2026, mes, 10), valor=Decimal("250.00"))
        )
    # Prevista não entra na evolução.
    lanc.registrar(
        transacao(
            data=date(2026, 7, 20),
            valor=Decimal("999.00"),
            status=StatusTransacao.PREVISTO,
        )
    )

    serie = ambiente["relatorios"].evolucao_mensal(
        date(2026, 6, 1), date(2026, 7, 31)
    )
    assert len(serie) == 2
    julho = serie[1]
    assert julho.mes == date(2026, 7, 1)
    assert julho.entradas == Decimal("1000.00")
    assert julho.saidas == Decimal("250.00")
    assert julho.saldo == Decimal("750.00")
    assert julho.taxa_poupanca == Decimal("75.0")


def test_detalhar_delega_filtros(ambiente):
    ambiente["lancamentos"].registrar(transacao())
    ambiente["lancamentos"].registrar(transacao(categoria_id=CAT_ALUGUEL))
    resultado = ambiente["relatorios"].detalhar(
        mes=date(2026, 7, 1), categoria_id=CAT_ALUGUEL
    )
    assert len(resultado) == 1
    assert resultado[0].categoria_id == CAT_ALUGUEL


# --------------------------------------------------------------- parâmetros


def test_remover_categoria_sem_transacoes_apaga(ambiente):
    nova = ambiente["parametros"].criar_categoria(
        Categoria(
            nome="Temporária",
            tipo=TipoCategoria.SAIDA,
            frequencia=Frequencia.VARIAVEL,
            prioridade=Prioridade.DISCRICIONARIA,
        )
    )
    assert ambiente["parametros"].remover_categoria(nova.id) is True
    assert ambiente["categorias"].buscar_por_id(nova.id) is None


def test_remover_categoria_com_transacoes_desativa(ambiente):
    ambiente["lancamentos"].registrar(transacao())
    assert ambiente["parametros"].remover_categoria(CAT_MERCADO) is False
    categoria = ambiente["categorias"].buscar_por_id(CAT_MERCADO)
    assert categoria is not None
    assert categoria.ativa is False


def test_remover_conta_com_transacoes_desativa(ambiente):
    ambiente["lancamentos"].registrar(transacao())
    assert ambiente["parametros"].remover_conta(CONTA_EUR) is False
    conta = ambiente["contas"].buscar_por_id(CONTA_EUR)
    assert conta.ativa is False


def test_reativar_categoria(ambiente):
    ambiente["lancamentos"].registrar(transacao())
    ambiente["parametros"].remover_categoria(CAT_MERCADO)
    reativada = ambiente["parametros"].reativar_categoria(CAT_MERCADO)
    assert reativada.ativa is True


def test_criar_conta_rejeita_tipo_invalido(ambiente):
    with pytest.raises(ErroValidacao):
        ambiente["parametros"].criar_conta(
            Conta(nome="X", moeda=Moeda.BRL, tipo="poupanca")
        )
