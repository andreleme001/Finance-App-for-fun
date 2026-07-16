"""Repositório de categorias."""

import sqlite3

from models.categoria import Categoria
from models.enums import Frequencia, Prioridade, TipoCategoria
from repositories.database import centavos_para_decimal, decimal_para_centavos


def _linha_para_categoria(linha: sqlite3.Row) -> Categoria:
    return Categoria(
        id=linha["id"],
        nome=linha["nome"],
        tipo=TipoCategoria(linha["tipo"]),
        frequencia=Frequencia(linha["frequencia"]),
        prioridade=Prioridade(linha["prioridade"]),
        orcado_mensal=centavos_para_decimal(linha["orcado_mensal_centavos"]),
        ativa=bool(linha["ativa"]),
    )


class CategoriaRepository:
    """CRUD de categorias."""

    def __init__(self, conexao: sqlite3.Connection) -> None:
        self._conexao = conexao

    def criar(self, categoria: Categoria) -> Categoria:
        cursor = self._conexao.execute(
            """
            INSERT INTO categoria (nome, tipo, frequencia, prioridade,
                                   orcado_mensal_centavos, ativa)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                categoria.nome,
                categoria.tipo.value,
                categoria.frequencia.value,
                categoria.prioridade.value,
                decimal_para_centavos(categoria.orcado_mensal),
                int(categoria.ativa),
            ),
        )
        self._conexao.commit()
        categoria.id = cursor.lastrowid
        return categoria

    def buscar_por_id(self, categoria_id: int) -> Categoria | None:
        linha = self._conexao.execute(
            "SELECT * FROM categoria WHERE id = ?", (categoria_id,)
        ).fetchone()
        return _linha_para_categoria(linha) if linha else None

    def atualizar(self, categoria: Categoria) -> None:
        self._conexao.execute(
            """
            UPDATE categoria SET nome = ?, tipo = ?, frequencia = ?,
                prioridade = ?, orcado_mensal_centavos = ?, ativa = ?
            WHERE id = ?
            """,
            (
                categoria.nome,
                categoria.tipo.value,
                categoria.frequencia.value,
                categoria.prioridade.value,
                decimal_para_centavos(categoria.orcado_mensal),
                int(categoria.ativa),
                categoria.id,
            ),
        )
        self._conexao.commit()

    def deletar(self, categoria_id: int) -> None:
        self._conexao.execute(
            "DELETE FROM categoria WHERE id = ?", (categoria_id,)
        )
        self._conexao.commit()

    def listar(self) -> list[Categoria]:
        linhas = self._conexao.execute(
            "SELECT * FROM categoria ORDER BY nome"
        ).fetchall()
        return [_linha_para_categoria(linha) for linha in linhas]

    def listar_ativas(self) -> list[Categoria]:
        linhas = self._conexao.execute(
            "SELECT * FROM categoria WHERE ativa = 1 ORDER BY nome"
        ).fetchall()
        return [_linha_para_categoria(linha) for linha in linhas]

    def possui_transacoes(self, categoria_id: int) -> bool:
        """Indica se há transações vinculadas à categoria."""
        linha = self._conexao.execute(
            "SELECT 1 FROM transacao WHERE categoria_id = ? LIMIT 1",
            (categoria_id,),
        ).fetchone()
        return linha is not None
