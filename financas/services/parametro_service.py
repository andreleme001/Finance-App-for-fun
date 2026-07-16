"""Serviço de parâmetros: manutenção de categorias e contas."""

from models.categoria import Categoria
from models.conta import Conta
from repositories.categoria_repository import CategoriaRepository
from repositories.conta_repository import ContaRepository
from services.lancamento_service import ErroValidacao

TIPOS_CONTA = ("corrente", "credito")


class ParametroService:
    """CRUD de categorias e contas, com desativação em vez de exclusão."""

    def __init__(
        self, categoria_repo: CategoriaRepository, conta_repo: ContaRepository
    ) -> None:
        self._categorias = categoria_repo
        self._contas = conta_repo

    # ------------------------------------------------------------ categorias

    def listar_categorias(
        self, somente_ativas: bool = False
    ) -> list[Categoria]:
        if somente_ativas:
            return self._categorias.listar_ativas()
        return self._categorias.listar()

    def criar_categoria(self, categoria: Categoria) -> Categoria:
        if not categoria.nome.strip():
            raise ErroValidacao("O nome da categoria não pode ser vazio.")
        if categoria.orcado_mensal < 0:
            raise ErroValidacao("O orçamento mensal não pode ser negativo.")
        return self._categorias.criar(categoria)

    def editar_categoria(self, categoria: Categoria) -> Categoria:
        if (
            categoria.id is None
            or self._categorias.buscar_por_id(categoria.id) is None
        ):
            raise ErroValidacao("Categoria inexistente.")
        if not categoria.nome.strip():
            raise ErroValidacao("O nome da categoria não pode ser vazio.")
        if categoria.orcado_mensal < 0:
            raise ErroValidacao("O orçamento mensal não pode ser negativo.")
        self._categorias.atualizar(categoria)
        return categoria

    def remover_categoria(self, categoria_id: int) -> bool:
        """Apaga a categoria; se houver transações, apenas desativa.

        Retorna True se apagou, False se desativou.
        """
        categoria = self._categorias.buscar_por_id(categoria_id)
        if categoria is None:
            raise ErroValidacao("Categoria inexistente.")
        if self._categorias.possui_transacoes(categoria_id):
            categoria.ativa = False
            self._categorias.atualizar(categoria)
            return False
        self._categorias.deletar(categoria_id)
        return True

    def reativar_categoria(self, categoria_id: int) -> Categoria:
        categoria = self._categorias.buscar_por_id(categoria_id)
        if categoria is None:
            raise ErroValidacao("Categoria inexistente.")
        categoria.ativa = True
        self._categorias.atualizar(categoria)
        return categoria

    # ---------------------------------------------------------------- contas

    def listar_contas(self, somente_ativas: bool = False) -> list[Conta]:
        if somente_ativas:
            return self._contas.listar_ativas()
        return self._contas.listar()

    def criar_conta(self, conta: Conta) -> Conta:
        if not conta.nome.strip():
            raise ErroValidacao("O nome da conta não pode ser vazio.")
        if conta.tipo not in TIPOS_CONTA:
            raise ErroValidacao(f"Tipo de conta deve ser um de {TIPOS_CONTA}.")
        return self._contas.criar(conta)

    def editar_conta(self, conta: Conta) -> Conta:
        if conta.id is None or self._contas.buscar_por_id(conta.id) is None:
            raise ErroValidacao("Conta inexistente.")
        if not conta.nome.strip():
            raise ErroValidacao("O nome da conta não pode ser vazio.")
        if conta.tipo not in TIPOS_CONTA:
            raise ErroValidacao(f"Tipo de conta deve ser um de {TIPOS_CONTA}.")
        self._contas.atualizar(conta)
        return conta

    def remover_conta(self, conta_id: int) -> bool:
        """Apaga a conta; se houver transações, apenas desativa.

        Retorna True se apagou, False se desativou.
        """
        conta = self._contas.buscar_por_id(conta_id)
        if conta is None:
            raise ErroValidacao("Conta inexistente.")
        if self._contas.possui_transacoes(conta_id):
            conta.ativa = False
            self._contas.atualizar(conta)
            return False
        self._contas.deletar(conta_id)
        return True

    def reativar_conta(self, conta_id: int) -> Conta:
        conta = self._contas.buscar_por_id(conta_id)
        if conta is None:
            raise ErroValidacao("Conta inexistente.")
        conta.ativa = True
        self._contas.atualizar(conta)
        return conta
