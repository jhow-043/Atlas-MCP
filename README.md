# Atlas MCP

[![CI](https://github.com/jhow-043/Atlas-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/jhow-043/Atlas-MCP/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

**MCP Server para contexto estruturado e RAG em projetos de engenharia de software.**

Atlas MCP é um servidor que implementa o [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol) para fornecer contexto estruturado a agentes LLM, com recuperação semântica via RAG (Retrieval-Augmented Generation).

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
│     │Context Layers│    │
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
├── src/atlas_mcp/          # Código-fonte principal
│   ├── protocol/           # Camada de protocolo MCP (JSON-RPC 2.0)
│   ├── resources/          # MCP Resources
│   ├── tools/              # MCP Tools
│   ├── context/            # Camadas de contexto
│   ├── vectorization/      # RAG (chunking, embeddings, busca)
│   ├── governance/         # Governança e ciclo de vida
│   └── persistence/        # Persistência e auditoria
├── tests/                  # Testes automatizados
│   ├── unit/               # Testes unitários
│   └── integration/        # Testes de integração
├── docs/                   # Documentação
│   ├── architecture/       # Documentos de arquitetura
│   ├── phases/             # Planejamento por fases
│   └── adr/                # Architecture Decision Records
├── .github/                # GitHub config
│   ├── governance/         # Políticas de governança
│   ├── workflows/          # GitHub Actions CI/CD
│   └── ISSUE_TEMPLATE/     # Templates de issues
├── scripts/                # Scripts utilitários
└── config/                 # Arquivos de configuração
```

---

## Documentação

- [Contexto do Projeto](docs/architecture/context.md)
- [Design de Arquitetura](docs/architecture/architecture-design.md)
- [ADRs](docs/adr/)
- [Guia de Contribuição](CONTRIBUTING.md)
- [Política de Branching](.github/governance/branching-policy.md)

---

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).
