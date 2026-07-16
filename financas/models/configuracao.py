"""Modelo de configuração local (valores fora do controle de versão)."""

from dataclasses import dataclass


@dataclass
class Configuracao:
    """Par chave/valor guardado no banco, nunca no código versionado.

    `privado=True` marca dados sensíveis (API keys, identificadores
    pessoais): qualquer exibição ou exportação deve mascará-los.
    """

    chave: str
    valor: str
    privado: bool = True
    descricao: str | None = None
    id: int | None = None
