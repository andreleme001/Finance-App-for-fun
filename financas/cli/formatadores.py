"""Formatação de saída com rich: tabelas e cores. Só esta camada formata."""

from datetime import date
from decimal import Decimal

from rich.console import Console
from rich.table import Table

from models.categoria import Categoria
from models.conta import Conta
from models.enums import Moeda, StatusTransacao, TipoCategoria
from models.transacao import Transacao
from services.relatorio_service import (
    ComparativoCategoria,
    EvolucaoMes,
    ResumoMensal,
)

console = Console()

SIMBOLOS = {Moeda.BRL: "R$", Moeda.EUR: "€"}

MESES_PT = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]


def nome_mes(mes: date) -> str:
    return f"{MESES_PT[mes.month - 1]}/{mes.year}"


def formatar_valor(valor: Decimal, moeda: Moeda) -> str:
    """Formata em estilo pt-BR: R$ 1.234,56 / € 1.234,56."""
    texto = (
        f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    )
    return f"{SIMBOLOS[moeda]} {texto}"


def valor_colorido(
    valor: Decimal, moeda: Moeda, invertido: bool = False
) -> str:
    """Verde para positivo, vermelho para negativo (ou o inverso)."""
    negativo = valor < 0
    if invertido:
        negativo = not negativo
    cor = "red" if negativo else "green"
    return f"[{cor}]{formatar_valor(valor, moeda)}[/{cor}]"


def tabela_resumo(resumo: ResumoMensal) -> Table:
    tabela = Table(title=f"Resumo de {nome_mes(resumo.mes)}")
    tabela.add_column("Moeda")
    tabela.add_column("Indicador")
    tabela.add_column("Previsto", justify="right")
    tabela.add_column("Realizado", justify="right")
    for bloco in resumo.moedas:
        m = bloco.moeda
        tabela.add_row(
            m.value,
            "Entradas",
            valor_colorido(bloco.entradas_previsto, m),
            valor_colorido(bloco.entradas_realizado, m),
        )
        tabela.add_row(
            "",
            "Saídas",
            valor_colorido(bloco.saidas_previsto, m, invertido=True),
            valor_colorido(bloco.saidas_realizado, m, invertido=True),
        )
        tabela.add_row(
            "",
            "Saldo do mês",
            valor_colorido(bloco.saldo_previsto, m),
            valor_colorido(bloco.saldo_realizado, m),
        )
        tabela.add_row(
            "",
            "Saldo acumulado",
            valor_colorido(bloco.saldo_acumulado_previsto, m),
            valor_colorido(bloco.saldo_acumulado_realizado, m),
            end_section=True,
        )
    return tabela


def tabela_comparativo(linhas: list[ComparativoCategoria], mes: date) -> Table:
    tabela = Table(title=f"Comparativo por categoria — {nome_mes(mes)}")
    tabela.add_column("Moeda")
    tabela.add_column("Categoria")
    tabela.add_column("Tipo")
    tabela.add_column("Orçado", justify="right")
    tabela.add_column("Previsto", justify="right")
    tabela.add_column("Realizado", justify="right")
    tabela.add_column("Diferença", justify="right")
    tabela.add_column("% usado", justify="right")
    for linha in linhas:
        m = linha.moeda
        estourou = linha.tipo is TipoCategoria.SAIDA and linha.diferenca < 0
        percentual = linha.percentual_utilizado
        if percentual is None:
            texto_percentual = "—"
        else:
            cor = "red" if percentual > 100 else "green"
            texto_percentual = f"[{cor}]{percentual}%[/{cor}]"
        tabela.add_row(
            m.value,
            linha.categoria_nome,
            "Entrada" if linha.tipo is TipoCategoria.ENTRADA else "Saída",
            formatar_valor(linha.orcado, m),
            formatar_valor(linha.previsto, m),
            formatar_valor(linha.realizado, m),
            valor_colorido(linha.diferenca, m)
            if linha.tipo is TipoCategoria.SAIDA
            else formatar_valor(linha.diferenca, m),
            texto_percentual,
            style="red" if estourou else None,
        )
    return tabela


def tabela_evolucao(serie: list[EvolucaoMes]) -> Table:
    tabela = Table(title="Evolução mensal (realizado)")
    tabela.add_column("Mês")
    tabela.add_column("Moeda")
    tabela.add_column("Entradas", justify="right")
    tabela.add_column("Saídas", justify="right")
    tabela.add_column("Saldo", justify="right")
    tabela.add_column("Poupança", justify="right")
    for ponto in serie:
        m = ponto.moeda
        taxa = ponto.taxa_poupanca
        if taxa is None:
            texto_taxa = "—"
        else:
            texto_taxa = f"[{'green' if taxa >= 0 else 'red'}]{taxa}%[/]"
        tabela.add_row(
            nome_mes(ponto.mes),
            m.value,
            valor_colorido(ponto.entradas, m),
            valor_colorido(ponto.saidas, m, invertido=True),
            valor_colorido(ponto.saldo, m),
            texto_taxa,
        )
    return tabela


def tabela_transacoes(
    transacoes: list[Transacao],
    categorias: dict[int, Categoria],
    contas: dict[int, Conta],
) -> Table:
    tabela = Table(title=f"Transações ({len(transacoes)})")
    tabela.add_column("Id", justify="right")
    tabela.add_column("Data")
    tabela.add_column("Descrição")
    tabela.add_column("Categoria")
    tabela.add_column("Conta")
    tabela.add_column("Valor", justify="right")
    tabela.add_column("Status")
    for t in transacoes:
        categoria = categorias[t.categoria_id]
        conta = contas[t.conta_id]
        entrada = categoria.tipo is TipoCategoria.ENTRADA
        status_previsto = t.status is StatusTransacao.PREVISTO
        tabela.add_row(
            str(t.id),
            t.data.strftime("%d/%m/%Y"),
            t.descricao
            if not t.subcategoria
            else f"{t.descricao} ({t.subcategoria})",
            categoria.nome,
            conta.nome,
            valor_colorido(t.valor, conta.moeda, invertido=not entrada),
            "[yellow]previsto[/yellow]" if status_previsto else "realizado",
        )
    return tabela


def tabela_categorias(categorias: list[Categoria]) -> Table:
    tabela = Table(title="Categorias")
    tabela.add_column("Id", justify="right")
    tabela.add_column("Nome")
    tabela.add_column("Tipo")
    tabela.add_column("Frequência")
    tabela.add_column("Prioridade")
    tabela.add_column("Orçado mensal", justify="right")
    tabela.add_column("Ativa")
    for c in categorias:
        tabela.add_row(
            str(c.id),
            c.nome,
            c.tipo.value.capitalize(),
            c.frequencia.value.capitalize(),
            c.prioridade.value.capitalize(),
            f"{c.orcado_mensal:.2f}".replace(".", ","),
            "[green]sim[/green]" if c.ativa else "[red]não[/red]",
        )
    return tabela


def tabela_contas(contas: list[Conta]) -> Table:
    tabela = Table(title="Contas")
    tabela.add_column("Id", justify="right")
    tabela.add_column("Nome")
    tabela.add_column("Moeda")
    tabela.add_column("Tipo")
    tabela.add_column("Ativa")
    for c in contas:
        tabela.add_row(
            str(c.id),
            c.nome,
            c.moeda.value,
            c.tipo,
            "[green]sim[/green]" if c.ativa else "[red]não[/red]",
        )
    return tabela
