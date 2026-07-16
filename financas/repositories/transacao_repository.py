"""Repositório de transações (único acesso SQL da entidade)."""

import sqlite3
from datetime import date, datetime

from models.enums import FormaPagamento, StatusTransacao
from models.transacao import Transacao
from repositories.database import centavos_para_decimal, decimal_para_centavos


def _linha_para_transacao(linha: sqlite3.Row) -> Transacao:
    return Transacao(
        id=linha["id"],
        data=date.fromisoformat(linha["data"]),
        descricao=linha["descricao"],
        valor=centavos_para_decimal(linha["valor_centavos"]),
        categoria_id=linha["categoria_id"],
        conta_id=linha["conta_id"],
        subcategoria=linha["subcategoria"],
        status=StatusTransacao(linha["status"]),
        forma_pagamento=(
            FormaPagamento(linha["forma_pagamento"])
            if linha["forma_pagamento"]
            else None
        ),
        observacoes=linha["observacoes"],
        criado_em=datetime.fromisoformat(linha["criado_em"]),
        atualizado_em=datetime.fromisoformat(linha["atualizado_em"]),
    )


class TransacaoRepository:
    """CRUD e listagem filtrada de transações."""

    def __init__(self, conexao: sqlite3.Connection) -> None:
        self._conexao = conexao

    def criar(self, transacao: Transacao) -> Transacao:
        """Insere a transação e retorna-a com id preenchido."""
        agora = datetime.now().isoformat(sep=" ", timespec="seconds")
        cursor = self._conexao.execute(
            """
            INSERT INTO transacao (
                data, descricao, valor_centavos, categoria_id, conta_id,
                subcategoria, status, forma_pagamento, observacoes,
                criado_em, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transacao.data.isoformat(),
                transacao.descricao,
                decimal_para_centavos(transacao.valor),
                transacao.categoria_id,
                transacao.conta_id,
                transacao.subcategoria,
                transacao.status.value,
                transacao.forma_pagamento.value
                if transacao.forma_pagamento
                else None,
                transacao.observacoes,
                agora,
                agora,
            ),
        )
        self._conexao.commit()
        transacao.id = cursor.lastrowid
        transacao.criado_em = datetime.fromisoformat(agora)
        transacao.atualizado_em = datetime.fromisoformat(agora)
        return transacao

    def buscar_por_id(self, transacao_id: int) -> Transacao | None:
        linha = self._conexao.execute(
            "SELECT * FROM transacao WHERE id = ?", (transacao_id,)
        ).fetchone()
        return _linha_para_transacao(linha) if linha else None

    def atualizar(self, transacao: Transacao) -> None:
        """Atualiza todos os campos editáveis; renova atualizado_em."""
        agora = datetime.now().isoformat(sep=" ", timespec="seconds")
        self._conexao.execute(
            """
            UPDATE transacao SET
                data = ?, descricao = ?, valor_centavos = ?,
                categoria_id = ?, conta_id = ?, subcategoria = ?,
                status = ?, forma_pagamento = ?,
                observacoes = ?, atualizado_em = ?
            WHERE id = ?
            """,
            (
                transacao.data.isoformat(),
                transacao.descricao,
                decimal_para_centavos(transacao.valor),
                transacao.categoria_id,
                transacao.conta_id,
                transacao.subcategoria,
                transacao.status.value,
                transacao.forma_pagamento.value
                if transacao.forma_pagamento
                else None,
                transacao.observacoes,
                agora,
                transacao.id,
            ),
        )
        self._conexao.commit()
        transacao.atualizado_em = datetime.fromisoformat(agora)

    def deletar(self, transacao_id: int) -> None:
        self._conexao.execute(
            "DELETE FROM transacao WHERE id = ?", (transacao_id,)
        )
        self._conexao.commit()

    def listar(
        self,
        mes: date | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        categoria_id: int | None = None,
        conta_id: int | None = None,
        status: StatusTransacao | None = None,
    ) -> list[Transacao]:
        """Lista transações combinando filtros opcionais; ordena por data."""
        condicoes: list[str] = []
        parametros: list[object] = []
        if mes is not None:
            condicoes.append("strftime('%Y-%m', data) = ?")
            parametros.append(f"{mes.year:04d}-{mes.month:02d}")
        if data_inicio is not None:
            condicoes.append("data >= ?")
            parametros.append(data_inicio.isoformat())
        if data_fim is not None:
            condicoes.append("data <= ?")
            parametros.append(data_fim.isoformat())
        if categoria_id is not None:
            condicoes.append("categoria_id = ?")
            parametros.append(categoria_id)
        if conta_id is not None:
            condicoes.append("conta_id = ?")
            parametros.append(conta_id)
        if status is not None:
            condicoes.append("status = ?")
            parametros.append(status.value)

        sql = "SELECT * FROM transacao"
        if condicoes:
            sql += " WHERE " + " AND ".join(condicoes)
        sql += " ORDER BY data, id"
        linhas = self._conexao.execute(sql, parametros).fetchall()
        return [_linha_para_transacao(linha) for linha in linhas]
