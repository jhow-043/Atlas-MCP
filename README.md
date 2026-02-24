# Atlas MCP

[![CI](https://github.com/jhow-043/Atlas-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/jhow-043/Atlas-MCP/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-93%25-brightgreen.svg)](https://github.com/jhow-043/Atlas-MCP)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-blueviolet.svg)](https://github.com/modelcontextprotocol)

**MCP Server de grau de produção para contexto estruturado e RAG em projetos de engenharia de software.**

O Atlas MCP implementa o [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol) para fornecer **memória estruturada** a agentes LLM — stack tecnológica, convenções, decisões arquiteturais e busca semântica via RAG (Retrieval-Augmented Generation) com PostgreSQL + pgvector.

---

## Status do Projeto

| Fase | Descrição | Status |
|------|-----------|--------|
| Fase 0 | Fundação do Repositório | ✅ Concluída |
| Fase 1 | Fundação e Protocolo MCP | ✅ Concluída |
| Fase 2 | Context Layers e Persistência | ✅ Concluída |
| Fase 3 | Vectorization, RAG e Tools Avançadas | ✅ Concluída |
| Fase 4 | Bootstrap, Wiring e Servidor Funcional | ✅ Concluída |
| Fase 5 | Documentação, Hardening e Release | ✅ Concluída |

> **640+ testes** · **93% de cobertura** · **4 tools** · **7 resources**

---

## Quick Start

### Opção 1: Docker (recomendado)

```bash
# Clonar o repositório
git clone https://github.com/jhow-043/Atlas-MCP.git
cd Atlas-MCP

# Copiar variáveis de ambiente e configurar
cp .env.example .env
# Editar .env com sua OPENAI_API_KEY (ou usar sentence-transformers local)

# Subir tudo (PostgreSQL + Atlas MCP)
docker compose up -d

# Verificar saúde dos serviços
docker compose ps
```

### Opção 2: Local (stdio)

```bash
# Clonar e instalar
git clone https://github.com/jhow-043/Atlas-MCP.git
cd Atlas-MCP
uv sync --all-extras

# Copiar e configurar variáveis de ambiente
cp .env.example .env

# Iniciar PostgreSQL (necessário para RAG)
docker compose up -d postgres

# Iniciar o servidor
uv run python -m atlas_mcp
```

### Opção 3: Sem banco de dados (modo degradado)

```bash
# O servidor funciona sem PostgreSQL — resources ok, RAG indisponível
uv run python -m atlas_mcp
```

> No modo degradado, resources como `context://core/stack` funcionam normalmente. Tools que dependem de RAG (`search_context`) retornam erro informativo.

---

## Resources

Resources são dados somente leitura acessíveis via URI:

| URI | Descrição |
|-----|-----------|
| `context://core/stack` | Stack tecnológica (dados reais de `pyproject.toml`) |
| `context://core/conventions` | Convenções de código (style, naming, testing) |
| `context://core/structure` | Estrutura de diretórios do projeto |
| `context://decisions/adrs` | Lista de ADRs registrados |
| `context://decisions/adrs/{id}` | Detalhes de um ADR específico |
| `context://governance/audit-log` | Trail de auditoria de governança |
| `context://workflow/current` | Workflow de desenvolvimento ativo |

---

## Tools

Tools são ações que o agente pode executar:

| Nome | Descrição | Requer DB? |
|------|-----------|------------|
| `search_context` | Busca semântica via RAG no contexto do projeto | ✅ |
| `plan_feature` | Planejamento estruturado de features com contexto | Opcional |
| `analyze_bug` | Análise estruturada de bugs com contexto | Opcional |
| `register_adr` | Criar e registrar um Architecture Decision Record | ✅ |

### Parâmetros das Tools

**`search_context`**
```
query (str, obrigatório) — Texto de busca semântica
filters (dict, opcional) — Filtros por tipo de documento
limit (int, opcional) — Máximo de resultados (padrão: 5)
similarity_threshold (float, opcional) — Limiar de similaridade 0–1 (padrão: 0.7)
```

**`plan_feature`**
```
title (str, obrigatório) — Nome da feature
description (str, obrigatório) — Descrição detalhada
requirements (list[str], opcional) — Requisitos
constraints (list[str], opcional) — Restrições
```

**`analyze_bug`**
```
title (str, obrigatório) — Título do bug
description (str, obrigatório) — Descrição do problema
expected_behavior (str, opcional) — Comportamento esperado
steps_to_reproduce (list[str], opcional) — Passos para reproduzir
```

**`register_adr`**
```
title (str, obrigatório) — Título da decisão
context (str, obrigatório) — Contexto da decisão
decision (str, obrigatório) — A decisão tomada
consequences (str, obrigatório) — Consequências
alternatives_considered (list[str], opcional) — Alternativas
tags (list[str], opcional) — Tags de categorização
```

---

## Arquitetura

```
┌──────────────────────────────┐
│    MCP Client (Claude, etc)  │
└────────────┬─────────────────┘
             │ JSON-RPC 2.0 (stdio/SSE)
             ▼
┌──────────────────────────────┐
│      Atlas MCP Server        │
│  ┌────────┬────────┬───────┐ │
│  │Resources│ Tools │Prompts│ │
│  └───┬────┴───┬────┴───┬───┘ │
│      ▼        ▼        ▼     │
│  ┌───────────────────────┐   │
│  │    Context Layers     │   │
│  │  Core · Workflow ·    │   │
│  │  Decision             │   │
│  └───────────┬───────────┘   │
│              ▼               │
│  ┌───────────────────────┐   │
│  │   Vectorization (RAG) │   │
│  │  Chunker → Embeddings │   │
│  │  → VectorStore        │   │
│  └───────────┬───────────┘   │
│              ▼               │
│  ┌───────────────────────┐   │
│  │ Governance &          │   │
│  │ Persistence           │   │
│  │ PostgreSQL + pgvector │   │
│  └───────────────────────┘   │
└──────────────────────────────┘
```

### Camadas de Contexto

| Camada | Descrição | Disponibilidade |
|--------|-----------|-----------------|
| **Core** | Stack, convenções, estrutura do projeto | Sempre disponível |
| **Workflow** | Contexto de feature, bug ou refactor em andamento | Ativado por workflow |
| **Decision** | ADRs aprovados e decisões arquiteturais | Sempre disponível |

### Pipeline RAG

1. **Chunking** — `MarkdownChunker` segmenta documentos por headers semânticos
2. **Embedding** — `EmbeddingProvider` (OpenAI ou Sentence Transformers) gera vetores
3. **Storage** — `VectorStore` persiste no pgvector com busca cosine similarity
4. **Indexação** — `IndexingService` orquestra chunk → embed → store
5. **Governança** — Documentos `APPROVED` são indexados automaticamente; `DEPRECATED` são removidos

---

## Configuração

Veja o [guia de configuração](docs/configuration.md) para detalhes completos.

### Variáveis de ambiente principais

| Variável | Descrição | Default |
|----------|-----------|---------|
| `POSTGRES_HOST` | Host do PostgreSQL | `localhost` |
| `POSTGRES_PORT` | Porta do PostgreSQL | `5432` |
| `POSTGRES_USER` | Usuário | `atlas` |
| `POSTGRES_PASSWORD` | Senha | `atlas_dev` |
| `POSTGRES_DB` | Nome do banco | `atlas_mcp` |
| `EMBEDDING_PROVIDER` | `openai` ou `sentence-transformers` | `openai` |
| `OPENAI_API_KEY` | API key do OpenAI | — |
| `ATLAS_TRANSPORT` | `stdio` ou `sse` | `stdio` |
| `ATLAS_LOG_LEVEL` | Nível de log | `INFO` |
| `ATLAS_LOG_FORMAT` | `text` ou `json` | `text` |

---

## Uso com Claude Desktop

Adicione ao seu `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "atlas-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "atlas_mcp"],
      "cwd": "/caminho/para/Atlas-MCP",
      "env": {
        "POSTGRES_HOST": "localhost",
        "EMBEDDING_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

> Para modo local sem API key, use `"EMBEDDING_PROVIDER": "sentence-transformers"`. Veja o [guia de uso](docs/usage.md) para mais exemplos.

---

## Estrutura do Projeto

```
Atlas-MCP/
├── src/atlas_mcp/              # Código-fonte principal
│   ├── __main__.py             # Entry point (python -m atlas_mcp)
│   ├── server.py               # Factory do servidor MCP
│   ├── bootstrap.py            # Wiring de startup e shutdown
│   ├── config/                 # Settings centralizado + logging
│   │   ├── settings.py         # Settings (env vars + .env)
│   │   └── logging.py          # Logging estruturado (text/json)
│   ├── protocol/               # Camada de protocolo MCP
│   │   ├── handler.py          # ProtocolHandler (lifecycle + transports)
│   │   └── errors.py           # Exceções JSON-RPC 2.0
│   ├── resources/              # 7 MCP Resources (URI-based)
│   ├── tools/                  # 4 MCP Tools
│   │   ├── executor.py         # ToolExecutor
│   │   ├── search_context.py   # RAG search
│   │   ├── plan_feature.py     # Feature planning
│   │   ├── analyze_bug.py      # Bug analysis
│   │   └── register_adr.py     # ADR registration
│   ├── context/                # Core, Decision, Workflow
│   ├── governance/             # GovernanceService + AuditLogger
│   ├── persistence/            # DatabaseManager + MigrationRunner
│   └── vectorization/          # Chunker, Embeddings, VectorStore, Indexing
├── tests/                      # 640+ testes (93% cobertura)
│   ├── unit/                   # Testes unitários
│   └── integration/            # Testes de integração (requer Docker)
├── docs/                       # Documentação
│   ├── architecture/           # Contexto e arquitetura
│   ├── phases/                 # Planejamento por fases
│   ├── adr/                    # Architecture Decision Records
│   ├── configuration.md        # Guia de configuração
│   ├── usage.md                # Guia de uso
│   └── deployment.md           # Guia de deployment
├── docker-compose.yml          # PostgreSQL 16 + pgvector + Atlas MCP
├── Dockerfile                  # Multi-stage build
└── pyproject.toml              # Configuração do projeto
```

---

## Testes

```bash
# Testes unitários
uv run pytest tests/unit/

# Testes de integração (requer Docker com PostgreSQL)
docker compose up -d postgres
uv run pytest tests/integration/

# Todos os testes com cobertura
uv run pytest --cov=src/atlas_mcp --cov-report=term-missing

# Validação completa (lint + format + types + testes)
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest
```

---

## Documentação

| Documento | Descrição |
|-----------|-----------|
| [Configuração](docs/configuration.md) | Variáveis de ambiente e modos de operação |
| [Uso](docs/usage.md) | Claude Desktop, MCP Inspector, exemplos |
| [Deployment](docs/deployment.md) | Docker Compose em produção, troubleshooting |
| [Contribuição](CONTRIBUTING.md) | Como contribuir, fluxo de desenvolvimento |
| [Arquitetura](docs/architecture/context.md) | Contexto e design do projeto |
| [ADRs](docs/adr/) | Architecture Decision Records |
| [Branching](.github/governance/branching-policy.md) | Política de branches |

---

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).
