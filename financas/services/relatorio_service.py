"""Serviço de relatórios; retorna dados estruturados, nunca texto formatado."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from models.enums import Moeda, StatusTransacao, TipoCategoria
from models.transacao import Transacao
from repositories.categoria_repository import CategoriaRepository
from repositories.conta_repository import ContaRepository
from repositories.transacao_repository import TransacaoRepository

ZERO = Decimal("0")


@dataclass
class TotaisMoeda:
    """Totais de um mês em uma moeda, separados por previsto x realizado."""

    moeda: Moeda
    entradas_previsto: Decimal = ZERO
    entradas_realizado: Decimal = ZERO
    saidas_previsto: Decimal = ZERO
    saidas_realizado: Decimal = ZERO
    saldo_acumulado_previsto: Decimal = ZERO
    saldo_acumulado_realizado: Decimal = ZERO

    @property
    def saldo_previsto(self) -> Decimal:
        return self.entradas_previsto - self.saidas_previsto

    @property
    def saldo_realizado(self) -> Decimal:
        return self.entradas_realizado - self.saidas_realizado


@dataclass
class ResumoMensal:
    """Resumo do mês, com um bloco de totais por moeda (sem conversão)."""

    mes: date
    moedas: list[TotaisMoeda] = field(default_factory=list)


@dataclass
class ComparativoCategoria:
    """Orçado x previsto x realizado de uma categoria em um mês/moeda."""

    categoria_id: int
    categoria_nome: str
    tipo: TipoCategoria
    moeda: Moeda
    orcado: Decimal
    previsto: Decimal
    realizado: Decimal

    @property
    def diferenca(self) -> Decimal:
        """Orçado menos realizado (positivo = dentro do orçamento)."""
        return self.orcado - self.realizado

    @property
    def percentual_utilizado(self) -> Decimal | None:
        """Realizado / orçado em %; None quando não há orçamento."""
        if self.orcado == 0:
            return None
        return (self.realizado / self.orcado * 100).quantize(Decimal("0.1"))


@dataclass
class EvolucaoMes:
    """Entradas, saídas e saldo realizados de um mês em uma moeda."""

    mes: date
    moeda: Moeda
    entradas: Decimal = ZERO
    saidas: Decimal = ZERO

    @property
    def saldo(self) -> Decimal:
        return self.entradas - self.saidas

    @property
    def taxa_poupanca(self) -> Decimal | None:
        """(entradas − saídas) / entradas em %; None sem entradas."""
        if self.entradas == 0:
            return None
        return (self.saldo / self.entradas * 100).quantize(Decimal("0.1"))


def _primeiro_dia(mes: date) -> date:
    return mes.replace(day=1)


class RelatorioService:
    """Consolida transações em resumos, comparativos e séries mensais."""

    def __init__(
        self,
        transacao_repo: TransacaoRepository,
        categoria_repo: CategoriaRepository,
        conta_repo: ContaRepository,
    ) -> None:
        self._transacoes = transacao_repo
        self._categorias = categoria_repo
        self._contas = conta_repo

    def _mapas(self):
        categorias = {c.id: c for c in self._categorias.listar()}
        contas = {c.id: c for c in self._contas.listar()}
        return categorias, contas

    def resumo_mensal(self, mes: date) -> ResumoMensal:
        """Totais do mês e saldo acumulado até o fim do mês, por moeda."""
        categorias, contas = self._mapas()
        ultimo_dia = (
            date(mes.year + 1, 1, 1)
            if mes.month == 12
            else date(mes.year, mes.month + 1, 1)
        )
        totais: dict[Moeda, TotaisMoeda] = {}

        def bloco(moeda: Moeda) -> TotaisMoeda:
            return totais.setdefault(moeda, TotaisMoeda(moeda=moeda))

        # Acumulado considera tudo até o fim do mês; o mês corrente também
        # alimenta os totais mensais.
        for t in self._transacoes.listar(data_fim=ultimo_dia):
            if t.data >= ultimo_dia:
                continue
            moeda = contas[t.conta_id].moeda
            tipo = categorias[t.categoria_id].tipo
            sinal = 1 if tipo is TipoCategoria.ENTRADA else -1
            b = bloco(moeda)
            if t.status is StatusTransacao.REALIZADO:
                b.saldo_acumulado_realizado += sinal * t.valor
            else:
                b.saldo_acumulado_previsto += sinal * t.valor
            if (t.data.year, t.data.month) == (mes.year, mes.month):
                if tipo is TipoCategoria.ENTRADA:
                    if t.status is StatusTransacao.REALIZADO:
                        b.entradas_realizado += t.valor
                    else:
                        b.entradas_previsto += t.valor
                else:
                    if t.status is StatusTransacao.REALIZADO:
                        b.saidas_realizado += t.valor
                    else:
                        b.saidas_previsto += t.valor

        blocos = sorted(totais.values(), key=lambda b: b.moeda.value)
        return ResumoMensal(mes=_primeiro_dia(mes), moedas=blocos)

    def comparativo_por_categoria(
        self, mes: date
    ) -> list[ComparativoCategoria]:
        """Orçado x previsto x realizado por categoria, separado por moeda.

        O orçamento da categoria não tem moeda própria: ele é repetido em
        cada bloco de moeda em que a categoria teve movimento.
        """
        categorias, contas = self._mapas()
        acumulado: dict[tuple[int, Moeda], ComparativoCategoria] = {}
        for t in self._transacoes.listar(mes=mes):
            categoria = categorias[t.categoria_id]
            moeda = contas[t.conta_id].moeda
            chave = (categoria.id, moeda)
            comp = acumulado.setdefault(
                chave,
                ComparativoCategoria(
                    categoria_id=categoria.id,
                    categoria_nome=categoria.nome,
                    tipo=categoria.tipo,
                    moeda=moeda,
                    orcado=categoria.orcado_mensal,
                    previsto=ZERO,
                    realizado=ZERO,
                ),
            )
            if t.status is StatusTransacao.REALIZADO:
                comp.realizado += t.valor
            else:
                comp.previsto += t.valor
        return sorted(
            acumulado.values(),
            key=lambda c: (c.moeda.value, c.tipo.value, c.categoria_nome),
        )

    def evolucao_mensal(self, inicio: date, fim: date) -> list[EvolucaoMes]:
        """Série mensal de entradas/saídas REALIZADAS por moeda."""
        categorias, contas = self._mapas()
        serie: dict[tuple[date, Moeda], EvolucaoMes] = {}
        transacoes = self._transacoes.listar(
            data_inicio=_primeiro_dia(inicio),
            data_fim=fim,
            status=StatusTransacao.REALIZADO,
        )
        for t in transacoes:
            mes = _primeiro_dia(t.data)
            moeda = contas[t.conta_id].moeda
            ponto = serie.setdefault(
                (mes, moeda), EvolucaoMes(mes=mes, moeda=moeda)
            )
            if categorias[t.categoria_id].tipo is TipoCategoria.ENTRADA:
                ponto.entradas += t.valor
            else:
                ponto.saidas += t.valor
        return sorted(serie.values(), key=lambda p: (p.mes, p.moeda.value))

    def detalhar(
        self,
        mes: date | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        categoria_id: int | None = None,
        conta_id: int | None = None,
        status: StatusTransacao | None = None,
    ) -> list[Transacao]:
        """Lista transações filtradas (delegação ao repositório)."""
        return self._transacoes.listar(
            mes=mes,
            data_inicio=data_inicio,
            data_fim=data_fim,
            categoria_id=categoria_id,
            conta_id=conta_id,
            status=status,
        )
