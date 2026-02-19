# Copilot Instructions — Atlas MCP

## Identidade do Projeto

Este é o **Atlas MCP** — um MCP Server de grau de produção que fornece contexto estruturado e recuperação semântica (RAG) para agentes LLM em projetos de engenharia de software.

**Repositório:** `https://github.com/jhow-043/Atlas-MCP`

## Idioma

Todas as respostas, documentação, comentários de código e mensagens de commit devem ser em **português brasileiro (pt-BR)**, exceto:
- Nomes de variáveis, funções, classes e módulos → **inglês**
- Mensagens de commit → **inglês** (Conventional Commits)
- Docstrings → **inglês**

## Stack Tecnológica

- **Linguagem:** Python ≥ 3.12
- **Runtime:** Asyncio
- **SDK:** `mcp` (SDK oficial Python do Model Context Protocol)
- **Gerenciador de pacotes:** `uv`
- **Banco de dados:** PostgreSQL 16 + pgvector
- **Testes:** pytest + pytest-asyncio + pytest-cov
- **Lint/Format:** Ruff
- **Type check:** mypy (strict mode)
- **CI:** GitHub Actions

## Estrutura do Projeto

```
Atlas-MCP/
├── src/atlas_mcp/          ← Pacote principal
│   ├── __init__.py
│   ├── __main__.py          ← Entrypoint
│   ├── server.py            ← Servidor MCP principal
│   ├── protocol/            ← JSON-RPC 2.0, capability negotiation
│   ├── resources/           ← MCP Resources (URI-based)
│   ├── tools/               ← MCP Tools (search_context, plan_feature, etc.)
│   ├── context/             ← Camadas de contexto (core, workflow, decision)
│   ├── vectorization/       ← Chunking semântico, embeddings, busca vetorial
│   ├── governance/          ← Ciclo de vida de documentos, auditoria
│   └── persistence/         ← Repositórios, conexão DB, migrações
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
│   ├── architecture/
│   ├── phases/
│   └── adr/
├── .github/
│   ├── governance/          ← Políticas de branching, commits, governança
│   ├── workflows/           ← GitHub Actions CI
│   └── ISSUE_TEMPLATE/
└── config/
```

## Padrões de Código

### Estilo

- Line length: **100 caracteres**
- Indentation: **4 espaços**
- Quotes: **aspas duplas** para strings
- Type hints: **obrigatórios** em toda assinatura de função/método
- Docstrings: **Google style**, em inglês

### Exemplo de módulo

```python
"""Module description in English."""

from __future__ import annotations

from typing import Any


class ExampleService:
    """Service that does something specific.

    Attributes:
        name: The service name.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the service operation.

        Args:
            input_data: The input parameters.

        Returns:
            A dictionary with the operation results.

        Raises:
            ValueError: If input_data is invalid.
        """
        if not input_data:
            raise ValueError("input_data cannot be empty")
        return {"status": "ok", "service": self.name}
```

### Imports

Ordem obrigatória (gerenciada pelo Ruff/isort):
1. Standard library
2. Third-party
3. Local application

Sempre usar `from __future__ import annotations`.

### Naming Conventions

| Elemento | Convenção | Exemplo |
|----------|-----------|---------|
| Pacotes/módulos | snake_case | `vector_service.py` |
| Classes | PascalCase | `VectorService` |
| Funções/métodos | snake_case | `search_context()` |
| Constantes | UPPER_SNAKE | `DEFAULT_SIMILARITY_THRESHOLD` |
| Variáveis | snake_case | `chunk_text` |
| Type aliases | PascalCase | `ChunkMetadata` |
| Privados | prefixo `_` | `_internal_method()` |

## Governança de Desenvolvimento

### Regra Absoluta

```
Planejamento → Revisão → Aprovação → Execução
```

**Nunca** gere código de implementação sem que exista um planejamento de fase aprovado.

### Fases

- Máximo **8 tarefas** por fase
- Cada tarefa é atômica e bem escopada
- Requisitos emergentes → nova fase, nunca implementação ad-hoc

### Branching

```
main ← develop ← phase/P# ← TIPO/P#-D#
```

- **Tipos:** `FET`, `BUG`, `REF`, `INF`, `DOC`, `TST`
- **Formato:** `TIPO/P<fase>-D<tarefa>` (ex: `FET/P1-D3`)
- **Nunca** commit direto em `main` ou `develop`

### Commits — Conventional Commits

```
<tipo>(<escopo>): <descrição em inglês>
```

Com escopo **obrigatório** `P#-D#`:

```
feat(P1-D3): implement ResourceRegistry with static resources
fix(P2-D1): fix JSON-RPC id validation in ProtocolHandler
docs(P0-D4): create README.md with badges and quick start
chore(P0-D3): configure pyproject.toml with dependencies
ci(P0-D6): configure GitHub Actions CI pipeline
test(P1-D6): add unit tests for ProtocolHandler
```

Tipos: `feat`, `fix`, `docs`, `chore`, `ci`, `test`, `refactor`, `style`, `perf`

## Validação Obrigatória

Antes de qualquer commit, o código **deve** passar:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest
```

## Padrões de Teste

### Localização

- Testes unitários: `tests/unit/test_<modulo>.py`
- Testes de integração: `tests/integration/test_<modulo>_integration.py`

### Convenções

```python
"""Tests for the ProtocolHandler module."""

import pytest


class TestProtocolHandler:
    """Tests for ProtocolHandler class."""

    async def test_should_parse_valid_jsonrpc_request(self) -> None:
        """Validate that a well-formed JSON-RPC request is parsed correctly."""
        # Arrange
        raw_request = '{"jsonrpc": "2.0", "method": "initialize", "id": 1}'

        # Act
        result = handler.parse(raw_request)

        # Assert
        assert result.method == "initialize"
        assert result.id == 1

    async def test_should_reject_invalid_jsonrpc_version(self) -> None:
        """Validate that non-2.0 jsonrpc version raises error."""
        with pytest.raises(InvalidRequestError):
            handler.parse('{"jsonrpc": "1.0", "method": "test", "id": 1}')
```

### Nomes de testes

- Prefixo: `test_should_` ou `test_when_`
- Descritivos: o nome deve explicar o que é validado
- Pattern AAA: Arrange → Act → Assert

## Arquitetura MCP

### Protocolo

- Comunicação: **JSON-RPC 2.0** via stdio ou SSE
- Capability negotiation obrigatória
- Error codes conforme spec JSON-RPC

### Resources (somente leitura, URI-based)

```
context://core/stack
context://core/conventions
context://core/structure
context://decisions/adrs
context://decisions/adrs/{id}
context://workflow/current
context://governance/audit-log
```

### Tools (ações com input/output tipado)

- `search_context(query, filters?, limit?, similarity_threshold?)`
- `plan_feature(title, description, requirements?, constraints?)`
- `analyze_bug(title, description, expected_behavior?, steps_to_reproduce?)`
- `register_adr(title, context, decision, consequences, alternatives_considered?, tags?)`

### Camadas de Contexto

1. **Core Context** — sempre disponível (stack, convenções, estrutura)
2. **Workflow Context** — ativado por feature/bug/refactor
3. **Decision Context** — ADRs aprovados, versionados

### Governança de Dados

```
PROPOSED → IN_REVIEW → APPROVED → (DEPRECATED)
                    ↘ REJECTED
```

- Somente documentos **APPROVED** são indexados no vetor
- Toda transição gera entrada em audit_log
- Versões anteriores preservadas

## O que NÃO fazer

- ❌ Não gere código fora do escopo da tarefa atual
- ❌ Não crie arquivos em locais fora da estrutura definida
- ❌ Não use `print()` — use logging estruturado
- ❌ Não ignore type hints
- ❌ Não faça commits sem seguir Conventional Commits
- ❌ Não implemente treinamento, fine-tuning ou aprendizado autônomo
- ❌ Não altere `main` ou `develop` diretamente
- ❌ Não crie tarefas além do limite de 8 por fase
- ❌ Não prossiga sem planejamento aprovado

## Referências

- [Política de Branching](governance/branching-policy.md)
- [Convenção de Commits](governance/commit-convention.md)
- [Governança de Desenvolvimento](governance/development-governance.md)
- [Aprovação de PRs](governance/pr-approval.md)
- [Documento de Arquitetura](../docs/architecture/context.md)
- [MCP Specification](https://github.com/modelcontextprotocol)
