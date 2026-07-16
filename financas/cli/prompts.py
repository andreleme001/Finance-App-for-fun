"""Coleta e validação de input do usuário no terminal."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import TypeVar

from cli.formatadores import console

T = TypeVar("T")

ERRO = "[red]Entrada inválida.[/red]"


def pedir_texto(
    rotulo: str, padrao: str | None = None, obrigatorio: bool = True
) -> str | None:
    """Lê texto; Enter devolve o padrão (ou None se opcional)."""
    sufixo = f" [{padrao}]" if padrao else ("" if obrigatorio else " [vazio]")
    while True:
        valor = input(f"{rotulo}{sufixo}: ").strip()
        if valor:
            return valor
        if padrao is not None:
            return padrao
        if not obrigatorio:
            return None
        console.print(ERRO)


def pedir_decimal(rotulo: str, padrao: Decimal | None = None) -> Decimal:
    """Lê um valor monetário; aceita vírgula ou ponto decimal."""
    sufixo = f" [{padrao}]" if padrao is not None else ""
    while True:
        texto = input(f"{rotulo}{sufixo}: ").strip()
        if not texto and padrao is not None:
            return padrao
        try:
            return Decimal(
                texto.replace(".", "").replace(",", ".")
                if "," in texto
                else texto
            )
        except InvalidOperation:
            console.print(ERRO + " Use por exemplo 1234,56")


def pedir_data(rotulo: str, padrao: date | None = None) -> date:
    """Lê uma data em DD/MM/AAAA ou AAAA-MM-DD; Enter devolve o padrão."""
    sufixo = f" [{padrao.strftime('%d/%m/%Y')}]" if padrao else ""
    while True:
        texto = input(f"{rotulo} (DD/MM/AAAA){sufixo}: ").strip()
        if not texto and padrao is not None:
            return padrao
        for formato in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(texto, formato).date()
            except ValueError:
                continue
        console.print(ERRO)


def pedir_mes(rotulo: str, padrao: date | None = None) -> date:
    """Lê um mês em MM/AAAA; devolve o primeiro dia do mês."""
    sufixo = f" [{padrao.strftime('%m/%Y')}]" if padrao else ""
    while True:
        texto = input(f"{rotulo} (MM/AAAA){sufixo}: ").strip()
        if not texto and padrao is not None:
            return padrao.replace(day=1)
        try:
            return datetime.strptime(texto, "%m/%Y").date().replace(day=1)
        except ValueError:
            console.print(ERRO)


def pedir_inteiro(
    rotulo: str, minimo: int | None = None, maximo: int | None = None
) -> int:
    while True:
        try:
            valor = int(input(f"{rotulo}: ").strip())
        except ValueError:
            console.print(ERRO)
            continue
        if (minimo is None or valor >= minimo) and (
            maximo is None or valor <= maximo
        ):
            return valor
        console.print(ERRO)


def confirmar(rotulo: str, padrao: bool = False) -> bool:
    sufixo = "[S/n]" if padrao else "[s/N]"
    texto = input(f"{rotulo} {sufixo}: ").strip().lower()
    if not texto:
        return padrao
    return texto in ("s", "sim", "y")


def escolher(
    rotulo: str,
    opcoes: list[tuple[T, str]],
    permitir_cancelar: bool = True,
) -> T | None:
    """Mostra opções numeradas; devolve o valor escolhido ou None."""
    console.print(f"\n[bold]{rotulo}[/bold]")
    for indice, (_, etiqueta) in enumerate(opcoes, start=1):
        console.print(f"  {indice}. {etiqueta}")
    if permitir_cancelar:
        console.print("  0. Cancelar/voltar")
    while True:
        escolha = pedir_inteiro(
            "Opção", minimo=0 if permitir_cancelar else 1, maximo=len(opcoes)
        )
        if escolha == 0:
            return None
        return opcoes[escolha - 1][0]
