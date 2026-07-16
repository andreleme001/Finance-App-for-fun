"""Serviço de lançamento e manutenção de transações."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from models.enums import StatusTransacao
from models.transacao import Transacao
from repositories.categoria_repository import CategoriaRepository
from repositories.conta_repository import ContaRepository
from repositories.transacao_repository import TransacaoRepository


class ErroValidacao(ValueError):
    """Erro de regra de negócio ao validar uma operação."""


class LancamentoService:
    """Regras de negócio para registrar, confirmar e manter transações."""

    def __init__(
        self,
        transacao_repo: TransacaoRepository,
        categoria_repo: CategoriaRepository,
        conta_repo: ContaRepository,
    ) -> None:
        self._transacoes = transacao_repo
        self._categorias = categoria_repo
        self._contas = conta_repo

    def _validar(self, transacao: Transacao) -> None:
        if transacao.valor <= 0:
            raise ErroValidacao(
                "O valor da transação deve ser maior que zero."
            )
        if not transacao.descricao.strip():
            raise ErroValidacao("A descrição não pode ser vazia.")
        categoria = self._categorias.buscar_por_id(transacao.categoria_id)
        if categoria is None:
            raise ErroValidacao(
                f"Categoria {transacao.categoria_id} não existe."
            )
        if not categoria.ativa:
            raise ErroValidacao(f"Categoria '{categoria.nome}' está inativa.")
        conta = self._contas.buscar_por_id(transacao.conta_id)
        if conta is None:
            raise ErroValidacao(f"Conta {transacao.conta_id} não existe.")
        if not conta.ativa:
            raise ErroValidacao(f"Conta '{conta.nome}' está inativa.")

    def registrar(self, transacao: Transacao) -> Transacao:
        """Valida e persiste uma nova transação."""
        self._validar(transacao)
        return self._transacoes.criar(transacao)

    def confirmar(
        self,
        transacao_id: int,
        valor_real: Decimal | None = None,
        data_real: date | None = None,
    ) -> Transacao:
        """Muda uma transação PREVISTO → REALIZADO, ajustando valor/data."""
        transacao = self._transacoes.buscar_por_id(transacao_id)
        if transacao is None:
            raise ErroValidacao(f"Transação {transacao_id} não existe.")
        if transacao.status is not StatusTransacao.PREVISTO:
            raise ErroValidacao(
                "Apenas transações previstas podem ser confirmadas."
            )
        if valor_real is not None:
            if valor_real <= 0:
                raise ErroValidacao("O valor real deve ser maior que zero.")
            transacao.valor = valor_real
        if data_real is not None:
            transacao.data = data_real
        transacao.status = StatusTransacao.REALIZADO
        self._transacoes.atualizar(transacao)
        return transacao

    def criar_recorrente(
        self, transacao_base: Transacao, meses: list[date]
    ) -> list[Transacao]:
        """Gera uma transação PREVISTA por data informada em `meses`."""
        if not meses:
            raise ErroValidacao(
                "Informe ao menos uma data para a recorrência."
            )
        self._validar(transacao_base)
        criadas: list[Transacao] = []
        for data_ocorrencia in meses:
            copia = replace(
                transacao_base,
                id=None,
                data=data_ocorrencia,
                status=StatusTransacao.PREVISTO,
            )
            criadas.append(self._transacoes.criar(copia))
        return criadas

    def editar(self, transacao: Transacao) -> Transacao:
        """Valida e atualiza uma transação existente."""
        if (
            transacao.id is None
            or self._transacoes.buscar_por_id(transacao.id) is None
        ):
            raise ErroValidacao("Transação inexistente.")
        self._validar(transacao)
        self._transacoes.atualizar(transacao)
        return transacao

    def remover(self, transacao_id: int) -> None:
        """Remove uma transação existente."""
        if self._transacoes.buscar_por_id(transacao_id) is None:
            raise ErroValidacao(f"Transação {transacao_id} não existe.")
        self._transacoes.deletar(transacao_id)
