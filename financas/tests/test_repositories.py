"""Testes da camada de repositórios com banco em memória."""

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from models import (
    Categoria,
    Conta,
    FormaPagamento,
    Frequencia,
    Moeda,
    Prioridade,
    StatusTransacao,
    TipoCategoria,
    Transacao,
)
from repositories import (
    CategoriaRepository,
    ConfiguracaoRepository,
    ContaRepository,
    TransacaoRepository,
    conectar,
    inicializar,
)
from repositories.database import (
    CATEGORIAS_SEED,
    CONTAS_SEED,
    MIGRACOES,
    centavos_para_decimal,
    decimal_para_centavos,
)


@pytest.fixture
def conexao():
    conexao = inicializar(":memory:")
    yield conexao
    conexao.close()


@pytest.fixture
def repo_transacao(conexao):
    return TransacaoRepository(conexao)


@pytest.fixture
def repo_categoria(conexao):
    return CategoriaRepository(conexao)


@pytest.fixture
def repo_conta(conexao):
    return ContaRepository(conexao)


def nova_transacao(**ajustes) -> Transacao:
    base = dict(
        data=date(2026, 7, 10),
        descricao="Teste",
        valor=Decimal("100.50"),
        categoria_id=1,
        conta_id=1,
        status=StatusTransacao.REALIZADO,
        forma_pagamento=FormaPagamento.PIX,
    )
    base.update(ajustes)
    return Transacao(**base)


# ---------------------------------------------------------------- conversões


def test_conversao_centavos_decimal():
    assert decimal_para_centavos(Decimal("100.50")) == 10050
    assert decimal_para_centavos(Decimal("0.01")) == 1
    assert centavos_para_decimal(10050) == Decimal("100.50")
    assert centavos_para_decimal(1) == Decimal("0.01")


# ------------------------------------------------------- inicialização/seed


def test_inicializar_aplica_schema_e_seed(conexao):
    versao = conexao.execute(
        "SELECT MAX(versao) AS v FROM schema_version"
    ).fetchone()
    assert versao["v"] == len(MIGRACOES)
    total_contas = conexao.execute(
        "SELECT COUNT(*) AS n FROM conta"
    ).fetchone()["n"]
    total_categorias = conexao.execute(
        "SELECT COUNT(*) AS n FROM categoria"
    ).fetchone()["n"]
    assert total_contas == len(CONTAS_SEED)
    assert total_categorias == len(CATEGORIAS_SEED)


def test_seed_nao_duplica_em_banco_existente(tmp_path):
    caminho = tmp_path / "financas.db"
    conexao1 = inicializar(caminho)
    conexao1.close()
    conexao2 = inicializar(caminho)
    total = conexao2.execute("SELECT COUNT(*) AS n FROM conta").fetchone()["n"]
    conexao2.close()
    assert total == len(CONTAS_SEED)


def test_foreign_keys_ativas(conexao, repo_transacao):
    with pytest.raises(sqlite3.IntegrityError):
        repo_transacao.criar(nova_transacao(categoria_id=9999))


# ------------------------------------------------------------------ transação


def test_transacao_criar_e_buscar(repo_transacao):
    criada = repo_transacao.criar(nova_transacao())
    assert criada.id is not None
    buscada = repo_transacao.buscar_por_id(criada.id)
    assert buscada is not None
    assert buscada.valor == Decimal("100.50")
    assert buscada.data == date(2026, 7, 10)
    assert buscada.status is StatusTransacao.REALIZADO
    assert buscada.forma_pagamento is FormaPagamento.PIX


def test_transacao_atualizar(repo_transacao):
    t = repo_transacao.criar(nova_transacao())
    t.valor = Decimal("250.00")
    t.descricao = "Alterada"
    repo_transacao.atualizar(t)
    buscada = repo_transacao.buscar_por_id(t.id)
    assert buscada.valor == Decimal("250.00")
    assert buscada.descricao == "Alterada"


def test_transacao_deletar(repo_transacao):
    t = repo_transacao.criar(nova_transacao())
    repo_transacao.deletar(t.id)
    assert repo_transacao.buscar_por_id(t.id) is None


def test_transacao_listar_filtros_combinados(repo_transacao):
    repo_transacao.criar(nova_transacao(data=date(2026, 6, 5)))
    repo_transacao.criar(nova_transacao(data=date(2026, 7, 1), categoria_id=2))
    repo_transacao.criar(
        nova_transacao(data=date(2026, 7, 20), status=StatusTransacao.PREVISTO)
    )

    assert len(repo_transacao.listar()) == 3
    assert len(repo_transacao.listar(mes=date(2026, 7, 1))) == 2
    assert len(repo_transacao.listar(categoria_id=2)) == 1
    assert len(repo_transacao.listar(status=StatusTransacao.PREVISTO)) == 1
    assert (
        len(
            repo_transacao.listar(
                mes=date(2026, 7, 1), status=StatusTransacao.REALIZADO
            )
        )
        == 1
    )
    assert (
        len(
            repo_transacao.listar(
                data_inicio=date(2026, 6, 1), data_fim=date(2026, 7, 10)
            )
        )
        == 2
    )


def test_transacao_valor_zero_rejeitado_pelo_schema(repo_transacao):
    with pytest.raises(sqlite3.IntegrityError):
        repo_transacao.criar(nova_transacao(valor=Decimal("0")))


# ------------------------------------------------------------------ categoria


def test_categoria_crud(repo_categoria):
    nova = Categoria(
        nome="Categoria Teste",
        tipo=TipoCategoria.SAIDA,
        frequencia=Frequencia.VARIAVEL,
        prioridade=Prioridade.DISCRICIONARIA,
        orcado_mensal=Decimal("300.00"),
    )
    criada = repo_categoria.criar(nova)
    assert criada.id is not None

    buscada = repo_categoria.buscar_por_id(criada.id)
    assert buscada.orcado_mensal == Decimal("300.00")

    buscada.ativa = False
    repo_categoria.atualizar(buscada)
    assert repo_categoria.buscar_por_id(criada.id).ativa is False
    assert all(c.id != criada.id for c in repo_categoria.listar_ativas())

    repo_categoria.deletar(criada.id)
    assert repo_categoria.buscar_por_id(criada.id) is None


def test_categoria_possui_transacoes(repo_categoria, repo_transacao):
    assert repo_categoria.possui_transacoes(1) is False
    repo_transacao.criar(nova_transacao(categoria_id=1))
    assert repo_categoria.possui_transacoes(1) is True


# --------------------------------------------------------------------- conta


def test_conta_crud(repo_conta):
    criada = repo_conta.criar(
        Conta(nome="Conta Teste", moeda=Moeda.EUR, tipo="corrente")
    )
    assert criada.id is not None

    buscada = repo_conta.buscar_por_id(criada.id)
    assert buscada.moeda is Moeda.EUR

    buscada.ativa = False
    repo_conta.atualizar(buscada)
    assert all(c.id != criada.id for c in repo_conta.listar_ativas())

    repo_conta.deletar(criada.id)
    assert repo_conta.buscar_por_id(criada.id) is None


def test_conta_seed_moedas(repo_conta):
    contas = {c.nome: c for c in repo_conta.listar()}
    assert contas["Conta Corrente EUR"].moeda is Moeda.EUR
    assert contas["Conta Corrente BRL"].moeda is Moeda.BRL
    assert contas["Cartão de Crédito BRL"].tipo == "credito"


# ------------------------------------------------------------- configuração


def test_configuracao_definir_e_obter(conexao):
    repo = ConfiguracaoRepository(conexao)
    criada = repo.definir(
        "api_cambio_chave", "segredo-123", descricao="API de câmbio"
    )
    assert criada.id is not None
    assert criada.privado is True  # padrão: tudo é privado

    buscada = repo.obter("api_cambio_chave")
    assert buscada.valor == "segredo-123"
    assert buscada.descricao == "API de câmbio"


def test_configuracao_definir_atualiza_sem_duplicar(conexao):
    repo = ConfiguracaoRepository(conexao)
    repo.definir("chave_x", "v1")
    repo.definir("chave_x", "v2", privado=False)
    assert len(repo.listar()) == 1
    atualizada = repo.obter("chave_x")
    assert atualizada.valor == "v2"
    assert atualizada.privado is False


def test_configuracao_remover(conexao):
    repo = ConfiguracaoRepository(conexao)
    repo.definir("temporaria", "x")
    repo.remover("temporaria")
    assert repo.obter("temporaria") is None


def test_migracao_v2_em_banco_v1(tmp_path):
    """Banco criado na v1 recebe a tabela configuracao ao reabrir."""
    caminho = tmp_path / "financas.db"
    conexao = conectar(caminho)
    conexao.executescript(MIGRACOES[0])
    conexao.execute("CREATE TABLE schema_version (versao INTEGER NOT NULL)")
    conexao.execute("INSERT INTO schema_version (versao) VALUES (1)")
    conexao.commit()
    conexao.close()

    conexao = inicializar(caminho)
    versao = conexao.execute(
        "SELECT MAX(versao) AS v FROM schema_version"
    ).fetchone()["v"]
    assert versao == len(MIGRACOES)
    # Sem re-seed (banco não era novo) e com a tabela nova utilizável.
    total = conexao.execute("SELECT COUNT(*) AS n FROM conta").fetchone()["n"]
    assert total == 0
    ConfiguracaoRepository(conexao).definir("chave", "valor")
    conexao.close()
