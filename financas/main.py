"""Ponto de entrada: monta as dependências e executa o menu."""

import argparse
from pathlib import Path

import config
from cli.menu import Menu
from repositories import (
    CategoriaRepository,
    ContaRepository,
    TransacaoRepository,
    inicializar,
)
from services import LancamentoService, ParametroService, RelatorioService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Planejamento financeiro pessoal"
    )
    parser.add_argument(
        "--banco",
        type=Path,
        default=config.CAMINHO_BANCO,
        help=f"caminho do arquivo SQLite (padrão: {config.CAMINHO_BANCO})",
    )
    argumentos = parser.parse_args()

    conexao = inicializar(argumentos.banco)
    transacao_repo = TransacaoRepository(conexao)
    categoria_repo = CategoriaRepository(conexao)
    conta_repo = ContaRepository(conexao)

    lancamentos = LancamentoService(transacao_repo, categoria_repo, conta_repo)
    relatorios = RelatorioService(transacao_repo, categoria_repo, conta_repo)
    parametros = ParametroService(categoria_repo, conta_repo)

    menu = Menu(lancamentos, relatorios, parametros)
    try:
        menu.executar()
    except (KeyboardInterrupt, EOFError):
        print("\nAté logo!")
    finally:
        conexao.close()


if __name__ == "__main__":
    main()
