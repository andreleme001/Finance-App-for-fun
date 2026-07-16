"""Testes básicos dos modelos e enums."""

from datetime import date, datetime
from decimal import Decimal

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


def test_enums_valores():
    assert TipoCategoria.ENTRADA.value == "ENTRADA"
    assert TipoCategoria.SAIDA.value == "SAIDA"
    assert Frequencia.FIXA.value == "FIXA"
    assert Prioridade.DISCRICIONARIA.value == "DISCRICIONARIA"
    assert StatusTransacao.PREVISTO.value == "PREVISTO"
    assert FormaPagamento.CARTAO_CREDITO.value == "CARTAO_CREDITO"
    assert Moeda.BRL.value == "BRL"
    assert Moeda.EUR.value == "EUR"


def test_enum_reconstrucao_a_partir_do_valor():
    assert StatusTransacao("REALIZADO") is StatusTransacao.REALIZADO
    assert FormaPagamento("PIX") is FormaPagamento.PIX


def test_transacao_criacao_e_padroes():
    t = Transacao(
        data=date(2026, 7, 16),
        descricao="Mercado da semana",
        valor=Decimal("152.30"),
        categoria_id=1,
        conta_id=2,
    )
    assert t.id is None
    assert t.valor == Decimal("152.30")
    assert isinstance(t.valor, Decimal)
    assert t.status is StatusTransacao.PREVISTO
    assert t.subcategoria is None
    assert t.forma_pagamento is None
    assert isinstance(t.criado_em, datetime)
    assert isinstance(t.atualizado_em, datetime)


def test_categoria_criacao_e_padroes():
    c = Categoria(
        nome="Aluguel",
        tipo=TipoCategoria.SAIDA,
        frequencia=Frequencia.FIXA,
        prioridade=Prioridade.ESSENCIAL,
    )
    assert c.id is None
    assert c.ativa is True
    assert c.orcado_mensal == Decimal("0")
    assert isinstance(c.orcado_mensal, Decimal)


def test_conta_criacao_e_padroes():
    c = Conta(nome="Conta Corrente EUR", moeda=Moeda.EUR, tipo="corrente")
    assert c.id is None
    assert c.ativa is True
    assert c.moeda is Moeda.EUR
