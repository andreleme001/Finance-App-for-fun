"""Repositório de contas."""

import sqlite3

from models.conta import Conta
from models.enums import Moeda


def _linha_para_conta(linha: sqlite3.Row) -> Conta:
    return Conta(
        id=linha["id"],
        nome=linha["nome"],
        moeda=Moeda(linha["moeda"]),
        tipo=linha["tipo"],
        ativa=bool(linha["ativa"]),
    )


class ContaRepository:
    """CRUD de contas."""

    def __init__(self, conexao: sqlite3.Connection) -> None:
        self._conexao = conexao

    def criar(self, conta: Conta) -> Conta:
        cursor = self._conexao.execute(
            "INSERT INTO conta (nome, moeda, tipo, ativa) VALUES (?, ?, ?, ?)",
            (conta.nome, conta.moeda.value, conta.tipo, int(conta.ativa)),
        )
        self._conexao.commit()
        conta.id = cursor.lastrowid
        return conta

    def buscar_por_id(self, conta_id: int) -> Conta | None:
        linha = self._conexao.execute(
            "SELECT * FROM conta WHERE id = ?", (conta_id,)
        ).fetchone()
        return _linha_para_conta(linha) if linha else None

    def atualizar(self, conta: Conta) -> None:
        self._conexao.execute(
            "UPDATE conta SET nome = ?, moeda = ?, tipo = ?, ativa = ? "
            "WHERE id = ?",
            (
                conta.nome,
                conta.moeda.value,
                conta.tipo,
                int(conta.ativa),
                conta.id,
            ),
        )
        self._conexao.commit()

    def deletar(self, conta_id: int) -> None:
        self._conexao.execute("DELETE FROM conta WHERE id = ?", (conta_id,))
        self._conexao.commit()

    def listar(self) -> list[Conta]:
        linhas = self._conexao.execute(
            "SELECT * FROM conta ORDER BY nome"
        ).fetchall()
        return [_linha_para_conta(linha) for linha in linhas]

    def listar_ativas(self) -> list[Conta]:
        linhas = self._conexao.execute(
            "SELECT * FROM conta WHERE ativa = 1 ORDER BY nome"
        ).fetchall()
        return [_linha_para_conta(linha) for linha in linhas]

    def possui_transacoes(self, conta_id: int) -> bool:
        """Indica se há transações vinculadas à conta."""
        linha = self._conexao.execute(
            "SELECT 1 FROM transacao WHERE conta_id = ? LIMIT 1", (conta_id,)
        ).fetchone()
        return linha is not None
