"""Modelo de categoria de transações."""

from dataclasses import dataclass
from decimal import Decimal

from models.enums import Frequencia, Prioridade, TipoCategoria


@dataclass
class Categoria:
    """Categoria que classifica transações e carrega orçamento mensal."""

    nome: str
    tipo: TipoCategoria
    frequencia: Frequencia
    prioridade: Prioridade
    orcado_mensal: Decimal = Decimal("0")
    ativa: bool = True
    id: int | None = None
