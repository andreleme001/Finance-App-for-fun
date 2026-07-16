"""Modelo de transação financeira."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from models.enums import FormaPagamento, StatusTransacao


@dataclass
class Transacao:
    """Lançamento financeiro vinculado a uma categoria e uma conta.

    O valor é sempre positivo; o sinal (entrada/saída) é derivado do tipo
    da categoria. O valor está na moeda da conta.
    """

    data: date
    descricao: str
    valor: Decimal
    categoria_id: int
    conta_id: int
    id: int | None = None
    subcategoria: str | None = None
    status: StatusTransacao = StatusTransacao.PREVISTO
    forma_pagamento: FormaPagamento | None = None
    observacoes: str | None = None
    criado_em: datetime = field(default_factory=datetime.now)
    atualizado_em: datetime = field(default_factory=datetime.now)
