# Atlas MCP

[![CI](https://github.com/jhow-043/Atlas-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/jhow-043/Atlas-MCP/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

**MCP Server para contexto estruturado e RAG em projetos de engenharia de software.**

Atlas MCP é um servidor que implementa o [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol) para fornecer contexto estruturado a agentes LLM, com recuperação semântica via RAG (Retrieval-Augmented Generation).

---

## Status do Projeto

| Fase | Descrição | Status |
|------|-----------|--------|
| Fase 0 | Fundação do Repositório | ✅ Concluída |
| Fase 1 | Fundação e Protocolo MCP | ✅ Concluída |
| Fase 2 | Camadas de Contexto e Vectorização | 🔜 Planejamento |

---

## Funcionalidades (Fase 1)

### Protocolo MCP

- **JSON-RPC 2.0** — comunicação via stdio transport
- **Capability Negotiation** — handshake `initialize`/`initialized` com declaração de capabilities
- **Error Handling** — erros padronizados conforme especificação JSON-RPC 2.0

### Resources

| URI | Descrição |
|-----|-----------|
| `context://core/stack` | Stack tecnológica do projeto (linguagem, runtime, SDK, banco de dados, ferramentas) |

### Tools

| Nome | Descrição |
|------|-----------|
| `search_context` | Busca semântica no contexto do projeto. Aceita `query`, `filters`, `limit` e `similarity_threshold`. (dados mock nesta fase) |

---

## Visão Geral da Arquitetura

```
┌────────────────────────┐
│     MCP Client (LLM)   │
└──────────┬─────────────┘
           │ JSON-RPC 2.0
           ▼
┌────────────────────────┐
│    Atlas MCP Server    │
│  ┌──────┬──────┬─────┐ │
│  │Resrc.│Tools │Prpts│ │
│  └──┬───┴──┬───┴──┬──┘ │
│     │Context Layers│   │
│  ┌──┴──────┴──────┴──┐ │
│  │  Vectorization    │ │
│  │  (RAG + pgvector) │ │
│  └───────────────────┘ │
│  ┌───────────────────┐ │
│  │   Governance &    │ │
│  │   Persistence     │ │
│  └───────────────────┘ │
└────────────────────────┘
```

### Camadas de Contexto

- **Core Context** — Stack tecnológica, convenções, estrutura (sempre disponível)
- **Workflow Context** — Contexto de feature, bug ou refactor (ativado por workflow)
- **Decision Context** — ADRs aprovados e decisões arquiteturais versionadas

---

## Quick Start

### Pré-requisitos

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) (gerenciador de pacotes)

### Instalação

```bash
# Clonar o repositório
git clone https://github.com/jhow-043/Atlas-MCP.git
cd Atlas-MCP

# Instalar dependências
uv sync --all-extras

# Executar o servidor
uv run python -m atlas_mcp
```

### Testes

```bash
# Executar testes
uv run pytest

# Com cobertura
uv run pytest --cov=src/atlas_mcp --cov-report=term-missing

# Lint e formatação
uv run ruff check .
uv run ruff format --check .

# Type checking
uv run mypy src/
```

---

## Estrutura do Projeto

```
Atlas-MCP/
├── src/atlas_mcp/              # Código-fonte principal
│   ├── __init__.py             # Versão do pacote
│   ├── __main__.py             # Entry point (python -m atlas_mcp)
│   ├── server.py               # Factory do servidor MCP
│   ├── protocol/               # Camada de protocolo MCP
│   │   ├── handler.py          # ProtocolHandler (lifecycle + stdio)
│   │   └── errors.py           # Exceções e helpers JSON-RPC 2.0
│   ├── resources/              # MCP Resources
│   │   ├── registry.py         # ResourceRegistry
│   │   └── core_stack.py       # Resource: context://core/stack
│   ├── tools/                  # MCP Tools
│   │   ├── executor.py         # ToolExecutor
│   │   └── search_context.py   # Tool: search_context (mock)
│   ├── context/                # Camadas de contexto (Fase 2)
│   ├── vectorization/          # RAG (Fase 2)
│   ├── governance/             # Governança e ciclo de vida (Fase 2)
│   └── persistence/            # Persistência e auditoria (Fase 2)
├── tests/                      # Testes automatizados
│   ├── unit/                   # Testes unitários (103 testes, 100% cobertura)
│   └── integration/            # Testes de integração
├── docs/                       # Documentação
│   ├── architecture/           # Documentos de arquitetura
│   ├── phases/                 # Planejamento por fases
│   ├── tasks/                  # Planning detalhado por tarefa
│   └── adr/                    # Architecture Decision Records
├── .github/                    # GitHub config
│   ├── governance/             # Políticas de governança
│   ├── workflows/              # GitHub Actions CI/CD
│   └── ISSUE_TEMPLATE/         # Templates de issues
├── scripts/                    # Scripts utilitários
└── config/                     # Arquivos de configuração
```

---

## Documentação

- [Contexto do Projeto](docs/architecture/context.md)
- [ADRs](docs/adr/)
- [Guia de Contribuição](CONTRIBUTING.md)
- [Política de Branching](.github/governance/branching-policy.md)

---

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).
