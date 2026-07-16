"""Loop principal do menu interativo."""

from datetime import date
from decimal import Decimal

from cli import formatadores, prompts
from cli.formatadores import console, formatar_valor
from models.categoria import Categoria
from models.conta import Conta
from models.enums import (
    FormaPagamento,
    Frequencia,
    Moeda,
    Prioridade,
    StatusTransacao,
    TipoCategoria,
)
from models.transacao import Transacao
from services import (
    ErroValidacao,
    LancamentoService,
    ParametroService,
    RelatorioService,
)

OPCOES_MENU = """
[bold cyan]=== Finanças pessoais ===[/bold cyan]
 1. Lançar transação
 2. Confirmar transações previstas do mês
 3. Resumo do mês
 4. Evolução mensal
 5. Detalhar transações
 6. Gerenciar categorias
 7. Gerenciar contas
 0. Sair
"""


class Menu:
    """Interface de terminal; só exibe dados e coleta input."""

    def __init__(
        self,
        lancamentos: LancamentoService,
        relatorios: RelatorioService,
        parametros: ParametroService,
    ) -> None:
        self._lancamentos = lancamentos
        self._relatorios = relatorios
        self._parametros = parametros

    def executar(self) -> None:
        """Roda o loop do menu até o usuário sair."""
        acoes = {
            1: self._lancar_transacao,
            2: self._confirmar_previstas,
            3: self._resumo_do_mes,
            4: self._evolucao_mensal,
            5: self._detalhar_transacoes,
            6: self._gerenciar_categorias,
            7: self._gerenciar_contas,
        }
        while True:
            console.print(OPCOES_MENU)
            opcao = prompts.pedir_inteiro("Opção", minimo=0, maximo=7)
            if opcao == 0:
                console.print("Até logo!")
                return
            try:
                acoes[opcao]()
            except ErroValidacao as erro:
                console.print(f"[red]Erro:[/red] {erro}")

    # ------------------------------------------------------------- auxiliares

    def _mapas(self):
        categorias = {c.id: c for c in self._parametros.listar_categorias()}
        contas = {c.id: c for c in self._parametros.listar_contas()}
        return categorias, contas

    def _escolher_categoria(self) -> Categoria | None:
        ativas = self._parametros.listar_categorias(somente_ativas=True)
        opcoes = [(c, f"{c.nome} ({c.tipo.value.lower()})") for c in ativas]
        return prompts.escolher("Categoria", opcoes)

    def _escolher_conta(self) -> Conta | None:
        ativas = self._parametros.listar_contas(somente_ativas=True)
        opcoes = [(c, f"{c.nome} ({c.moeda.value}, {c.tipo})") for c in ativas]
        return prompts.escolher("Conta", opcoes)

    # ------------------------------------------------------------- opção 1

    def _lancar_transacao(self) -> None:
        categoria = self._escolher_categoria()
        if categoria is None:
            return
        conta = self._escolher_conta()
        if conta is None:
            return
        descricao = prompts.pedir_texto("Descrição")
        valor = prompts.pedir_decimal(f"Valor ({conta.moeda.value})")
        data = prompts.pedir_data("Data", padrao=date.today())
        status = prompts.escolher(
            "Status",
            [
                (StatusTransacao.REALIZADO, "Realizado"),
                (StatusTransacao.PREVISTO, "Previsto"),
            ],
            permitir_cancelar=False,
        )
        forma = prompts.escolher(
            "Forma de pagamento (0 = nenhuma)",
            [(f, f.value.replace("_", " ").lower()) for f in FormaPagamento],
        )
        subcategoria = prompts.pedir_texto("Subcategoria", obrigatorio=False)
        observacoes = prompts.pedir_texto("Observações", obrigatorio=False)

        transacao = Transacao(
            data=data,
            descricao=descricao,
            valor=valor,
            categoria_id=categoria.id,
            conta_id=conta.id,
            subcategoria=subcategoria,
            status=status,
            forma_pagamento=forma,
            observacoes=observacoes,
        )

        if prompts.confirmar("Repetir como recorrência em outros meses?"):
            quantidade = prompts.pedir_inteiro(
                "Quantos meses (incluindo este)?", minimo=1, maximo=60
            )
            meses = []
            ano, mes = data.year, data.month
            for _ in range(quantidade):
                meses.append(date(ano, mes, min(data.day, 28)))
                mes += 1
                if mes > 12:
                    mes, ano = 1, ano + 1
            criadas = self._lancamentos.criar_recorrente(transacao, meses)
            console.print(
                f"[green]{len(criadas)} transações previstas criadas "
                f"({criadas[0].data.strftime('%m/%Y')} a "
                f"{criadas[-1].data.strftime('%m/%Y')}).[/green]"
            )
        else:
            criada = self._lancamentos.registrar(transacao)
            console.print(
                f"[green]Transação {criada.id} registrada: "
                f"{criada.descricao}, "
                f"{formatar_valor(criada.valor, conta.moeda)}.[/green]"
            )

    # ------------------------------------------------------------- opção 2

    def _confirmar_previstas(self) -> None:
        mes = prompts.pedir_mes("Mês", padrao=date.today())
        while True:
            previstas = self._relatorios.detalhar(
                mes=mes, status=StatusTransacao.PREVISTO
            )
            if not previstas:
                console.print(
                    "[yellow]Nenhuma transação prevista no mês.[/yellow]"
                )
                return
            categorias, contas = self._mapas()
            console.print(
                formatadores.tabela_transacoes(previstas, categorias, contas)
            )
            opcoes = [
                (
                    t,
                    f"{t.data.strftime('%d/%m')} — {t.descricao} — "
                    f"{formatar_valor(t.valor, contas[t.conta_id].moeda)}",
                )
                for t in previstas
            ]
            escolhida = prompts.escolher("Confirmar qual transação?", opcoes)
            if escolhida is None:
                return
            valor_real = prompts.pedir_decimal(
                "Valor real", padrao=escolhida.valor
            )
            data_real = prompts.pedir_data("Data real", padrao=escolhida.data)
            confirmada = self._lancamentos.confirmar(
                escolhida.id, valor_real=valor_real, data_real=data_real
            )
            console.print(
                f"[green]Transação {confirmada.id} confirmada "
                "como realizada.[/green]"
            )

    # ------------------------------------------------------------- opção 3

    def _resumo_do_mes(self) -> None:
        mes = prompts.pedir_mes("Mês", padrao=date.today())
        resumo = self._relatorios.resumo_mensal(mes)
        if not resumo.moedas:
            console.print("[yellow]Sem transações até este mês.[/yellow]")
            return
        console.print(formatadores.tabela_resumo(resumo))
        comparativo = self._relatorios.comparativo_por_categoria(mes)
        if comparativo:
            console.print(formatadores.tabela_comparativo(comparativo, mes))

    # ------------------------------------------------------------- opção 4

    def _evolucao_mensal(self) -> None:
        hoje = date.today()
        inicio_padrao = (
            date(hoje.year - 1, hoje.month, 1)
            if hoje.month != 12
            else (date(hoje.year, 1, 1))
        )
        inicio = prompts.pedir_mes("Mês inicial", padrao=inicio_padrao)
        fim = prompts.pedir_mes("Mês final", padrao=hoje)
        ultimo_dia = (
            date(fim.year + 1, 1, 1)
            if fim.month == 12
            else date(fim.year, fim.month + 1, 1)
        )
        serie = self._relatorios.evolucao_mensal(inicio, ultimo_dia)
        if not serie:
            console.print(
                "[yellow]Sem transações realizadas no período.[/yellow]"
            )
            return
        console.print(formatadores.tabela_evolucao(serie))

    # ------------------------------------------------------------- opção 5

    def _detalhar_transacoes(self) -> None:
        mes = None
        if prompts.confirmar("Filtrar por mês?", padrao=True):
            mes = prompts.pedir_mes("Mês", padrao=date.today())
        categoria = conta = None
        if prompts.confirmar("Filtrar por categoria?"):
            categoria = self._escolher_categoria()
        if prompts.confirmar("Filtrar por conta?"):
            conta = self._escolher_conta()
        status = prompts.escolher(
            "Status (0 = todos)",
            [
                (StatusTransacao.PREVISTO, "Previsto"),
                (StatusTransacao.REALIZADO, "Realizado"),
            ],
        )
        transacoes = self._relatorios.detalhar(
            mes=mes,
            categoria_id=categoria.id if categoria else None,
            conta_id=conta.id if conta else None,
            status=status,
        )
        if not transacoes:
            console.print("[yellow]Nenhuma transação encontrada.[/yellow]")
            return
        categorias, contas = self._mapas()
        console.print(
            formatadores.tabela_transacoes(transacoes, categorias, contas)
        )

    # ------------------------------------------------------------- opção 6

    def _gerenciar_categorias(self) -> None:
        while True:
            acao = prompts.escolher(
                "Gerenciar categorias",
                [
                    ("listar", "Listar todas"),
                    ("criar", "Criar nova"),
                    ("editar", "Editar (nome, orçamento, atributos)"),
                    ("remover", "Remover/desativar"),
                    ("reativar", "Reativar"),
                ],
            )
            if acao is None:
                return
            if acao == "listar":
                console.print(
                    formatadores.tabela_categorias(
                        self._parametros.listar_categorias()
                    )
                )
            elif acao == "criar":
                self._criar_categoria()
            elif acao == "editar":
                self._editar_categoria()
            elif acao == "remover":
                self._remover_categoria()
            elif acao == "reativar":
                self._reativar_categoria()

    def _perguntar_atributos_categoria(
        self, base: Categoria | None = None
    ) -> tuple[TipoCategoria, Frequencia, Prioridade, Decimal]:
        tipo = prompts.escolher(
            "Tipo",
            [
                (TipoCategoria.SAIDA, "Saída"),
                (TipoCategoria.ENTRADA, "Entrada"),
            ],
            permitir_cancelar=False,
        )
        frequencia = prompts.escolher(
            "Frequência",
            [(Frequencia.VARIAVEL, "Variável"), (Frequencia.FIXA, "Fixa")],
            permitir_cancelar=False,
        )
        prioridade = prompts.escolher(
            "Prioridade",
            [
                (Prioridade.ESSENCIAL, "Essencial"),
                (Prioridade.DISCRICIONARIA, "Discricionária"),
            ],
            permitir_cancelar=False,
        )
        orcado = prompts.pedir_decimal(
            "Orçamento mensal",
            padrao=base.orcado_mensal if base else Decimal("0"),
        )
        return tipo, frequencia, prioridade, orcado

    def _criar_categoria(self) -> None:
        nome = prompts.pedir_texto("Nome")
        tipo, frequencia, prioridade, orcado = (
            self._perguntar_atributos_categoria()
        )
        criada = self._parametros.criar_categoria(
            Categoria(
                nome=nome,
                tipo=tipo,
                frequencia=frequencia,
                prioridade=prioridade,
                orcado_mensal=orcado,
            )
        )
        console.print(
            f"[green]Categoria '{criada.nome}' criada "
            f"(id {criada.id}).[/green]"
        )

    def _editar_categoria(self) -> None:
        todas = self._parametros.listar_categorias()
        categoria = prompts.escolher(
            "Qual categoria?", [(c, c.nome) for c in todas]
        )
        if categoria is None:
            return
        categoria.nome = prompts.pedir_texto("Nome", padrao=categoria.nome)
        if prompts.confirmar("Alterar tipo/frequência/prioridade/orçamento?"):
            (
                categoria.tipo,
                categoria.frequencia,
                categoria.prioridade,
                categoria.orcado_mensal,
            ) = self._perguntar_atributos_categoria(categoria)
        else:
            categoria.orcado_mensal = prompts.pedir_decimal(
                "Orçamento mensal", padrao=categoria.orcado_mensal
            )
        self._parametros.editar_categoria(categoria)
        console.print("[green]Categoria atualizada.[/green]")

    def _remover_categoria(self) -> None:
        ativas = self._parametros.listar_categorias(somente_ativas=True)
        categoria = prompts.escolher(
            "Qual categoria?", [(c, c.nome) for c in ativas]
        )
        if categoria is None:
            return
        if not prompts.confirmar(f"Confirmar remoção de '{categoria.nome}'?"):
            return
        apagou = self._parametros.remover_categoria(categoria.id)
        if apagou:
            console.print("[green]Categoria apagada.[/green]")
        else:
            console.print(
                "[yellow]Categoria possui transações: "
                "foi apenas desativada.[/yellow]"
            )

    def _reativar_categoria(self) -> None:
        inativas = [
            c for c in self._parametros.listar_categorias() if not c.ativa
        ]
        if not inativas:
            console.print("[yellow]Não há categorias inativas.[/yellow]")
            return
        categoria = prompts.escolher(
            "Qual categoria?", [(c, c.nome) for c in inativas]
        )
        if categoria is None:
            return
        self._parametros.reativar_categoria(categoria.id)
        console.print("[green]Categoria reativada.[/green]")

    # ------------------------------------------------------------- opção 7

    def _gerenciar_contas(self) -> None:
        while True:
            acao = prompts.escolher(
                "Gerenciar contas",
                [
                    ("listar", "Listar todas"),
                    ("criar", "Criar nova"),
                    ("editar", "Editar"),
                    ("remover", "Remover/desativar"),
                    ("reativar", "Reativar"),
                ],
            )
            if acao is None:
                return
            if acao == "listar":
                console.print(
                    formatadores.tabela_contas(
                        self._parametros.listar_contas()
                    )
                )
            elif acao == "criar":
                self._criar_conta()
            elif acao == "editar":
                self._editar_conta()
            elif acao == "remover":
                self._remover_conta()
            elif acao == "reativar":
                self._reativar_conta()

    def _criar_conta(self) -> None:
        nome = prompts.pedir_texto("Nome")
        moeda = prompts.escolher(
            "Moeda", [(m, m.value) for m in Moeda], permitir_cancelar=False
        )
        tipo = prompts.escolher(
            "Tipo",
            [("corrente", "Corrente"), ("credito", "Crédito")],
            permitir_cancelar=False,
        )
        criada = self._parametros.criar_conta(
            Conta(nome=nome, moeda=moeda, tipo=tipo)
        )
        console.print(
            f"[green]Conta '{criada.nome}' criada (id {criada.id}).[/green]"
        )

    def _editar_conta(self) -> None:
        todas = self._parametros.listar_contas()
        conta = prompts.escolher("Qual conta?", [(c, c.nome) for c in todas])
        if conta is None:
            return
        conta.nome = prompts.pedir_texto("Nome", padrao=conta.nome)
        conta.moeda = prompts.escolher(
            "Moeda", [(m, m.value) for m in Moeda], permitir_cancelar=False
        )
        conta.tipo = prompts.escolher(
            "Tipo",
            [("corrente", "Corrente"), ("credito", "Crédito")],
            permitir_cancelar=False,
        )
        self._parametros.editar_conta(conta)
        console.print("[green]Conta atualizada.[/green]")

    def _remover_conta(self) -> None:
        ativas = self._parametros.listar_contas(somente_ativas=True)
        conta = prompts.escolher("Qual conta?", [(c, c.nome) for c in ativas])
        if conta is None:
            return
        if not prompts.confirmar(f"Confirmar remoção de '{conta.nome}'?"):
            return
        apagou = self._parametros.remover_conta(conta.id)
        if apagou:
            console.print("[green]Conta apagada.[/green]")
        else:
            console.print(
                "[yellow]Conta possui transações: "
                "foi apenas desativada.[/yellow]"
            )

    def _reativar_conta(self) -> None:
        inativas = [c for c in self._parametros.listar_contas() if not c.ativa]
        if not inativas:
            console.print("[yellow]Não há contas inativas.[/yellow]")
            return
        conta = prompts.escolher(
            "Qual conta?", [(c, c.nome) for c in inativas]
        )
        if conta is None:
            return
        self._parametros.reativar_conta(conta.id)
        console.print("[green]Conta reativada.[/green]")
