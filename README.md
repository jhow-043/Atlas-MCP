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
| Fase 2 | Context Layers e Persistência | ✅ Concluída |
| Fase 3 | Vectorization e RAG | 🔜 Planejamento |

---

## Funcionalidades

### Protocolo MCP

- **JSON-RPC 2.0** — comunicação via stdio transport
- **Capability Negotiation** — handshake `initialize`/`initialized` com declaração de capabilities
- **Error Handling** — erros padronizados conforme especificação JSON-RPC 2.0

### Resources

| URI | Descrição |
|-----|-----------|
| `context://core/stack` | Stack tecnológica do projeto (dados reais de pyproject.toml) |
| `context://core/conventions` | Convenções de código (style, naming, testing) |
| `context://core/structure` | Estrutura de diretórios do projeto |
| `context://decisions/adrs` | Lista de ADRs do projeto |
| `context://decisions/adrs/{id}` | Detalhes de um ADR específico |
| `context://governance/audit-log` | Trail de auditoria de governança |
| `context://workflow/current` | Workflow de desenvolvimento ativo |

### Tools

| Nome | Descrição |
|------|-----------|
| `search_context` | Busca semântica no contexto do projeto (dados mock — RAG real na Fase 3) |
| `register_adr` | Criar e registrar um novo Architecture Decision Record |

### Persistência

- **PostgreSQL 16 + pgvector** via Docker Compose
- **DatabaseManager** — pool de conexões asyncpg com lifecycle management
- **MigrationRunner** — schema migrations transacionais
- **GovernanceService** — ciclo de vida de documentos (PROPOSED → APPROVED → DEPRECATED)
- **AuditLogger** — registra transições no audit_log

### Contexto

- **Core Context** — lê dados reais de `pyproject.toml` e `ruff.toml`
- **Decision Context** — parser de ADRs Markdown com regex
- **Workflow Context** — gerenciamento de workflow ativo com história de transições

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
- Docker e Docker Compose (para PostgreSQL)

### Instalação

```bash
# Clonar o repositório
git clone https://github.com/jhow-043/Atlas-MCP.git
cd Atlas-MCP

# Instalar dependências
uv sync --all-extras

# Copiar variáveis de ambiente
cp .env.example .env

# Iniciar PostgreSQL (opcional — necessário para persistência)
docker compose up -d

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
├── docker-compose.yml          # PostgreSQL 16 + pgvector
├── .env.example                # Variáveis de ambiente (template)
├── src/atlas_mcp/              # Código-fonte principal
│   ├── __init__.py             # Versão do pacote
│   ├── __main__.py             # Entry point (python -m atlas_mcp)
│   ├── server.py               # Factory do servidor MCP
│   ├── protocol/               # Camada de protocolo MCP
│   │   ├── handler.py          # ProtocolHandler (lifecycle + stdio)
│   │   └── errors.py           # Exceções e helpers JSON-RPC 2.0
│   ├── resources/              # MCP Resources (7 resources)
│   │   ├── registry.py         # ResourceRegistry
│   │   ├── core_stack.py       # context://core/stack
│   │   ├── core_conventions.py # context://core/conventions
│   │   ├── core_structure.py   # context://core/structure
│   │   ├── decision_adrs.py    # context://decisions/adrs[/{id}]
│   │   ├── governance_audit.py # context://governance/audit-log
│   │   └── workflow_current.py # context://workflow/current
│   ├── tools/                  # MCP Tools
│   │   ├── executor.py         # ToolExecutor
│   │   ├── search_context.py   # Tool: search_context (mock)
│   │   └── register_adr.py     # Tool: register_adr
│   ├── context/                # Camadas de contexto
│   │   ├── core.py             # CoreContextProvider
│   │   ├── decision.py         # DecisionContextProvider
│   │   └── workflow.py         # WorkflowContextProvider
│   ├── governance/             # Governança e ciclo de vida
│   │   ├── service.py          # GovernanceService
│   │   └── audit.py            # AuditLogger
│   ├── persistence/            # Persistência e banco de dados
│   │   ├── config.py           # DatabaseConfig
│   │   ├── database.py         # DatabaseManager
│   │   └── migrations.py       # MigrationRunner
│   └── vectorization/          # RAG (Fase 3)
├── tests/                      # Testes automatizados (319 testes, 97% cobertura)
│   ├── unit/                   # Testes unitários
│   └── integration/            # Testes de integração (requer Docker)
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
