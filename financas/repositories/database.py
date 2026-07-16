"""Conexão SQLite, criação de tabelas, migrações e seed inicial."""

import sqlite3
from decimal import Decimal
from pathlib import Path

from models.enums import Frequencia, Moeda, Prioridade, TipoCategoria

MIGRACOES: list[str] = [
    # Versão 1: schema inicial.
    """
    CREATE TABLE categoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        tipo TEXT NOT NULL CHECK (tipo IN ('ENTRADA', 'SAIDA')),
        frequencia TEXT NOT NULL CHECK (frequencia IN ('FIXA', 'VARIAVEL')),
        prioridade TEXT NOT NULL
            CHECK (prioridade IN ('ESSENCIAL', 'DISCRICIONARIA')),
        orcado_mensal_centavos INTEGER NOT NULL DEFAULT 0,
        ativa INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE conta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        moeda TEXT NOT NULL CHECK (moeda IN ('BRL', 'EUR')),
        tipo TEXT NOT NULL CHECK (tipo IN ('corrente', 'credito')),
        ativa INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE transacao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT NOT NULL,
        descricao TEXT NOT NULL,
        valor_centavos INTEGER NOT NULL CHECK (valor_centavos > 0),
        categoria_id INTEGER NOT NULL REFERENCES categoria(id),
        conta_id INTEGER NOT NULL REFERENCES conta(id),
        subcategoria TEXT,
        status TEXT NOT NULL CHECK (status IN ('PREVISTO', 'REALIZADO')),
        forma_pagamento TEXT,
        observacoes TEXT,
        criado_em TEXT NOT NULL,
        atualizado_em TEXT NOT NULL
    );

    CREATE INDEX idx_transacao_data ON transacao(data);
    CREATE INDEX idx_transacao_categoria ON transacao(categoria_id);
    CREATE INDEX idx_transacao_conta ON transacao(conta_id);
    """,
    # Versão 2: configurações locais (segredos/API keys ficam no banco,
    # que nunca é versionado no git — flag `privado` marca o que deve ser
    # mascarado em qualquer exibição ou exportação).
    """
    CREATE TABLE configuracao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chave TEXT NOT NULL UNIQUE,
        valor TEXT NOT NULL,
        privado INTEGER NOT NULL DEFAULT 1,
        descricao TEXT
    );
    """,
]

CONTAS_SEED: list[tuple[str, Moeda, str]] = [
    ("Conta Corrente EUR", Moeda.EUR, "corrente"),
    ("Conta Corrente BRL", Moeda.BRL, "corrente"),
    ("Cartão de Crédito BRL", Moeda.BRL, "credito"),
]

# Aliases curtos apenas para o seed caber em 79 colunas.
_ENT, _SAI = TipoCategoria.ENTRADA, TipoCategoria.SAIDA
_FIX, _VAR = Frequencia.FIXA, Frequencia.VARIAVEL
_ESS, _DIS = Prioridade.ESSENCIAL, Prioridade.DISCRICIONARIA

CATEGORIAS_SEED: list[tuple[str, TipoCategoria, Frequencia, Prioridade]] = [
    ("Salário Líquido", _ENT, _FIX, _ESS),
    ("Renda Extra / Freelance", _ENT, _VAR, _ESS),
    ("Rendimentos de Investimentos", _ENT, _VAR, _ESS),
    ("Reembolsos", _ENT, _VAR, _ESS),
    ("Outras Entradas", _ENT, _VAR, _ESS),
    ("Aluguel", _SAI, _FIX, _ESS),
    ("Utilidades (Água, Luz, Gás)", _SAI, _FIX, _ESS),
    ("Internet/Telefone", _SAI, _FIX, _ESS),
    ("Plano de Saúde/Seguro", _SAI, _FIX, _ESS),
    ("Alimentação/Mercado", _SAI, _VAR, _ESS),
    ("Transporte", _SAI, _VAR, _ESS),
    ("Saúde (Farmácia/Consultas)", _SAI, _VAR, _ESS),
    ("Assinaturas", _SAI, _FIX, _DIS),
    ("Lazer/Entretenimento", _SAI, _VAR, _DIS),
    ("Restaurantes/Delivery", _SAI, _VAR, _DIS),
    ("Compras", _SAI, _VAR, _DIS),
    ("Viagens", _SAI, _VAR, _DIS),
    ("Cuidados Pessoais", _SAI, _VAR, _DIS),
    ("Presentes/Doações", _SAI, _VAR, _DIS),
    ("Reserva de Emergência", _SAI, _FIX, _ESS),
    ("Investimentos", _SAI, _FIX, _ESS),
    ("Meta: Entrada do Carro", _SAI, _FIX, _ESS),
    ("Financiamento de Veículo", _SAI, _FIX, _ESS),
    ("Empréstimo Estudantil", _SAI, _FIX, _ESS),
    ("Cartão de Crédito (Parcelamentos)", _SAI, _VAR, _ESS),
]


def centavos_para_decimal(centavos: int) -> Decimal:
    """Converte inteiro em centavos para Decimal com 2 casas."""
    return Decimal(centavos) / Decimal(100)


def decimal_para_centavos(valor: Decimal) -> int:
    """Converte Decimal para inteiro em centavos (arredondamento exato)."""
    centavos = (valor * 100).to_integral_value()
    return int(centavos)


def conectar(caminho: str | Path) -> sqlite3.Connection:
    """Abre conexão SQLite com foreign keys ativas e row_factory."""
    if isinstance(caminho, Path):
        caminho.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(str(caminho))
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def _versao_atual(conexao: sqlite3.Connection) -> int:
    conexao.execute(
        "CREATE TABLE IF NOT EXISTS schema_version (versao INTEGER NOT NULL)"
    )
    linha = conexao.execute(
        "SELECT MAX(versao) AS v FROM schema_version"
    ).fetchone()
    return linha["v"] or 0


def aplicar_migracoes(conexao: sqlite3.Connection) -> int:
    """Aplica migrações pendentes; retorna a versão inicial do schema."""
    versao_inicial = _versao_atual(conexao)
    for versao, sql in enumerate(MIGRACOES, start=1):
        if versao > versao_inicial:
            conexao.executescript(sql)
            conexao.execute(
                "INSERT INTO schema_version (versao) VALUES (?)", (versao,)
            )
    conexao.commit()
    return versao_inicial


def popular_seed(conexao: sqlite3.Connection) -> None:
    """Insere contas e categorias iniciais (banco recém-criado)."""
    conexao.executemany(
        "INSERT INTO conta (nome, moeda, tipo) VALUES (?, ?, ?)",
        [(nome, moeda.value, tipo) for nome, moeda, tipo in CONTAS_SEED],
    )
    conexao.executemany(
        "INSERT INTO categoria (nome, tipo, frequencia, prioridade) "
        "VALUES (?, ?, ?, ?)",
        [
            (nome, tipo.value, freq.value, prio.value)
            for nome, tipo, freq, prio in CATEGORIAS_SEED
        ],
    )
    conexao.commit()


def inicializar(caminho: str | Path) -> sqlite3.Connection:
    """Abre o banco, aplica migrações e roda o seed na primeira execução."""
    conexao = conectar(caminho)
    versao_anterior = aplicar_migracoes(conexao)
    if versao_anterior == 0:
        popular_seed(conexao)
    return conexao
