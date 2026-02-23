# Guia de Contribuição — Atlas MCP

Obrigado pelo interesse em contribuir com o Atlas MCP! Este documento descreve como configurar o ambiente, o fluxo de trabalho e as convenções que seguimos.

---

## Pré-requisitos

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) (gerenciador de pacotes)
- Git
- Docker e Docker Compose (para testes de integração)

## Setup Local

```bash
# Clone o repositório
git clone https://github.com/jhow-043/Atlas-MCP.git
cd Atlas-MCP

# Instale todas as dependências (incluindo dev)
uv sync --all-extras

# Copie o template de variáveis de ambiente
cp .env.example .env
# Edite .env com sua OPENAI_API_KEY (ou use sentence-transformers)

# Inicie o PostgreSQL (necessário para testes de integração)
docker compose up -d postgres

# Verifique se está tudo funcionando
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest
```

### Setup sem Docker (modo degradado)

Para contribuir sem Docker, testes unitários funcionam normalmente:

```bash
uv sync --all-extras
uv run pytest tests/unit/
```

Testes de integração serão pulados automaticamente se o PostgreSQL não estiver disponível.

---

## Executando Testes

```bash
# Todos os testes (unit + integration se DB disponível)
uv run pytest

# Apenas testes unitários (sem Docker)
uv run pytest tests/unit/

# Apenas testes de integração (requer Docker)
uv run pytest tests/integration/

# Com cobertura
uv run pytest --cov=src/atlas_mcp --cov-report=term-missing

# Teste específico
uv run pytest tests/unit/test_server.py -v

# Testes em modo verbose
uv run pytest -v --tb=short
```

## Validação Completa

Antes de abrir um PR, garanta que **todos** os checks passam:

```bash
uv run ruff check .           # Lint
uv run ruff format --check .  # Formatação
uv run mypy src/              # Type checking (strict)
uv run pytest                 # Testes
```

---

## Política de Branching

Seguimos uma política rigorosa de branching documentada em [`.github/governance/branching-policy.md`](.github/governance/branching-policy.md).

### Resumo

```
main ← develop ← phase/P# ← TIPO/P#-D#
```

- **`main`** — Código estável, pronto para produção. Sem commits diretos.
- **`develop`** — Staging. Recebe merges de fases concluídas.
- **`phase/P#`** — Branch de fase. Recebe merges de tarefas.
- **`TIPO/P#-D#`** — Branch de tarefa individual.

### Tipos de Branch

| Tipo  | Uso                                    |
|-------|----------------------------------------|
| `FET` | Nova funcionalidade                    |
| `BUG` | Correção de defeito                    |
| `REF` | Refatoração                            |
| `INF` | Infraestrutura / setup / configuração  |
| `DOC` | Documentação                           |
| `TST` | Testes isolados                        |

### Exemplos

```
FET/P1-D3    # Feature, Fase 1, Tarefa 3
BUG/P2-D1    # Bug fix, Fase 2, Tarefa 1
INF/P0-D7    # Infra, Fase 0, Tarefa 7
```

---

## Convenção de Commits

Seguimos **Conventional Commits** com escopo obrigatório `(P#-D#)`:

```
<tipo>(<escopo>): <descrição>
```

### Exemplos

```
feat(P1-D3): implementar ResourceRegistry com resource estático
fix(P2-D1): corrigir parse de JSON-RPC na validação de id
docs(P0-D4): criar README.md com badges e quick start
chore(P0-D3): configurar pyproject.toml com dependências
ci(P0-D7): configurar GitHub Actions para CI
test(P1-D6): adicionar testes unitários do ProtocolHandler
refactor(P3-D5): extrair lógica de chunking para módulo dedicado
```

### Tipos de Commit

| Tipo       | Quando usar                            |
|------------|----------------------------------------|
| `feat`     | Nova funcionalidade                    |
| `fix`      | Correção de bug                        |
| `docs`     | Alteração em documentação              |
| `chore`    | Tarefas de manutenção / setup          |
| `ci`       | Alteração em CI/CD                     |
| `test`     | Adição ou correção de testes           |
| `refactor` | Refatoração sem alterar comportamento  |
| `style`    | Formatação, sem mudança de lógica      |
| `perf`     | Melhoria de performance                |

Documentação completa: [`.github/governance/commit-convention.md`](.github/governance/commit-convention.md)

---

## Processo de Pull Request

1. Crie sua branch a partir de `phase/P#` seguindo a convenção de nomes.
2. Implemente **apenas** o escopo da tarefa atribuída.
3. Garanta que todos os checks passam:
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run mypy src/`
   - `uv run pytest`
4. Abra um Pull Request para `phase/P#`.
5. Preencha o template de PR.
6. Após CI passar, realize o merge (self-merge permitido).

---

## Governança

O desenvolvimento segue fases com no máximo **8 tarefas** cada, obedecendo o ciclo:

> **Planejamento → Revisão → Aprovação → Execução**

Detalhes completos: [`.github/governance/development-governance.md`](.github/governance/development-governance.md)

---

## Como Adicionar uma Nova Tool

1. Crie o módulo em `src/atlas_mcp/tools/` (ex: `my_tool.py`)
2. Implemente a função `register_my_tool(server: FastMCP)` com o decorator `@server.tool()`
3. Registre a tool no `ToolExecutor` em `src/atlas_mcp/tools/executor.py`
4. Adicione testes unitários em `tests/unit/test_my_tool.py`
5. Documente a tool no README e no guia de uso

### Template básico

```python
"""Tool: my_tool — Description of the tool."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

def register_my_tool(server: FastMCP) -> None:
    """Register the my_tool tool on the server."""

    @server.tool(name="my_tool", description="...")
    async def my_tool(param: str) -> str:
        """Tool implementation."""
        # Implementação
        return "result"
```

## Como Adicionar um Novo Resource

1. Crie o módulo em `src/atlas_mcp/resources/` (ex: `my_resource.py`)
2. Implemente a função `register_my_resource(server: FastMCP)` com o decorator `@server.resource()`
3. Registre o resource no `ResourceRegistry` em `src/atlas_mcp/resources/registry.py`
4. Adicione testes unitários em `tests/unit/test_my_resource.py`
5. Documente o resource no README e no guia de uso

---

## Documentação Adicional

| Documento | Descrição |
|-----------|-----------|
| [Configuração](docs/configuration.md) | Variáveis de ambiente detalhadas |
| [Uso](docs/usage.md) | Exemplos com Claude Desktop e MCP Inspector |
| [Deployment](docs/deployment.md) | Docker Compose em produção |
| [Arquitetura](docs/architecture/context.md) | Contexto e design do projeto |
| [ADRs](docs/adr/) | Architecture Decision Records |
