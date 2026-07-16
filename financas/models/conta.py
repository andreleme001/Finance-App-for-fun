"""Modelo de conta financeira."""

from dataclasses import dataclass

from models.enums import Moeda


@dataclass
class Conta:
    """Conta onde as transações ocorrem; define a moeda dos valores."""

    nome: str
    moeda: Moeda
    tipo: str  # "corrente" | "credito"
    ativa: bool = True
    id: int | None = None
