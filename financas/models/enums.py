"""Enums do domínio financeiro."""

from enum import Enum


class TipoCategoria(Enum):
    """Natureza da categoria: entrada ou saída de dinheiro."""

    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"


class Frequencia(Enum):
    """Recorrência esperada da categoria."""

    FIXA = "FIXA"
    VARIAVEL = "VARIAVEL"


class Prioridade(Enum):
    """Prioridade do gasto da categoria."""

    ESSENCIAL = "ESSENCIAL"
    DISCRICIONARIA = "DISCRICIONARIA"


class StatusTransacao(Enum):
    """Estado da transação: prevista ou já realizada."""

    PREVISTO = "PREVISTO"
    REALIZADO = "REALIZADO"


class FormaPagamento(Enum):
    """Meio de pagamento utilizado na transação."""

    PIX = "PIX"
    DEBITO = "DEBITO"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    DINHEIRO = "DINHEIRO"
    TRANSFERENCIA = "TRANSFERENCIA"
    BOLETO = "BOLETO"


class Moeda(Enum):
    """Moeda da conta."""

    BRL = "BRL"
    EUR = "EUR"
