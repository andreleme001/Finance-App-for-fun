"""Configurações do sistema de finanças."""

from pathlib import Path

from models.enums import Moeda

DIR_BASE = Path(__file__).resolve().parent
CAMINHO_BANCO = DIR_BASE / "data" / "financas.db"
MOEDA_PADRAO = Moeda.BRL
