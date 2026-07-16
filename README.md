# Finance-App-for-fun

App de controle de finanças criado por mim para diversão, aplicação de
conceitos aprendidos durante meus estudos na Universidade de Maastricht e
também expor um pouco das minhas ideias e trabalho, como um portifólio.

Sistema de planejamento financeiro e controle de gastos pessoal, em Python,
com interface de terminal (CLI). Projetado em camadas para que a interface
possa ser substituída por uma API web (FastAPI) no futuro sem alterar as
camadas de baixo.

## Arquitetura

```
┌─────────────────────────────────────┐
│  INTERFACE (cli/)                   │  só exibe e coleta input
├─────────────────────────────────────┤
│  SERVIÇOS (services/)               │  resumos, validações, regras
├─────────────────────────────────────┤
│  REPOSITÓRIOS (repositories/)       │  único lugar que fala SQL
├─────────────────────────────────────┤
│  MODELOS (models/)                  │  Transacao, Categoria, Conta
└─────────────────────────────────────┘
```

- Persistência em SQLite puro (stdlib `sqlite3`), com migrações controladas
  por `schema_version`.
- Valores monetários como inteiro em centavos no banco e `Decimal` nos
  modelos — nunca float.
- Multi-moeda (BRL/EUR) por conta; relatórios nunca somam moedas diferentes.
- Soft delete (flag `ativa`) para categorias/contas com transações.

## Requisitos

- Python 3.10+
- [rich](https://github.com/Textualize/rich) (única dependência de runtime)
- pytest e ruff apenas para desenvolvimento

```bash
python3 -m venv .venv
.venv/bin/pip install rich pytest ruff
```

## Uso

```bash
cd financas
../.venv/bin/python main.py            # cria data/financas.db na 1ª execução
../.venv/bin/python main.py --banco x  # caminho alternativo do banco
```

Na primeira execução o banco é criado com um conjunto inicial de categorias
e contas genéricas — renomeie/edite pelas opções "Gerenciar categorias" e
"Gerenciar contas" do menu.

## Testes e lint

```bash
cd financas && ../.venv/bin/python -m pytest tests/
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

## Privacidade

Nenhum dado pessoal vive no código: o banco (`data/`), extratos e planilhas
estão no `.gitignore`. Segredos (ex.: chaves de API) devem ser guardados na
tabela `configuracao` do banco local — com `privado=1`, que marca o valor
para ser mascarado em qualquer exibição ou exportação.
