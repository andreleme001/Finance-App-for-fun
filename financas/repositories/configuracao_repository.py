"""Repositório de configurações locais."""

import sqlite3

from models.configuracao import Configuracao


def _linha_para_configuracao(linha: sqlite3.Row) -> Configuracao:
    return Configuracao(
        id=linha["id"],
        chave=linha["chave"],
        valor=linha["valor"],
        privado=bool(linha["privado"]),
        descricao=linha["descricao"],
    )


class ConfiguracaoRepository:
    """Acesso chave/valor às configurações guardadas no banco."""

    def __init__(self, conexao: sqlite3.Connection) -> None:
        self._conexao = conexao

    def definir(
        self,
        chave: str,
        valor: str,
        privado: bool = True,
        descricao: str | None = None,
    ) -> Configuracao:
        """Cria ou atualiza (upsert) a configuração da chave."""
        self._conexao.execute(
            """
            INSERT INTO configuracao (chave, valor, privado, descricao)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chave) DO UPDATE SET
                valor = excluded.valor,
                privado = excluded.privado,
                descricao = excluded.descricao
            """,
            (chave, valor, int(privado), descricao),
        )
        self._conexao.commit()
        return self.obter(chave)

    def obter(self, chave: str) -> Configuracao | None:
        linha = self._conexao.execute(
            "SELECT * FROM configuracao WHERE chave = ?", (chave,)
        ).fetchone()
        return _linha_para_configuracao(linha) if linha else None

    def listar(self) -> list[Configuracao]:
        linhas = self._conexao.execute(
            "SELECT * FROM configuracao ORDER BY chave"
        ).fetchall()
        return [_linha_para_configuracao(linha) for linha in linhas]

    def remover(self, chave: str) -> None:
        self._conexao.execute(
            "DELETE FROM configuracao WHERE chave = ?", (chave,)
        )
        self._conexao.commit()
