# Fase 2 — Context Layers e Infraestrutura de Persistência

**Status:** APROVADO  
**Data:** 2026-02-23  
**Versão:** 1.0  
**Repositório:** `https://github.com/jhow-043/Atlas-MCP.git`

---

## 1. Objetivo da Fase

Transicionar o Atlas MCP de dados mock para **contexto real**, implementando:

- Infraestrutura de persistência com PostgreSQL 16 + pgvector via Docker
- As 3 camadas de contexto (Core, Workflow, Decision) com dados reais
- 6 novos Resources MCP lendo dados do filesystem e do banco de dados
- Modelo de governança com ciclo de vida de documentos e audit logging
- Tool `register_adr` para registrar ADRs via protocolo MCP
- Testes de integração com banco de dados real via Docker

Ao final desta fase, o servidor deve fornecer **contexto estruturado real** ao LLM — stack, convenções, estrutura de diretórios, ADRs e workflow ativo.

**Projeto alvo:** Cloud-First Multi-Purpose AI Platform — a modular, enterprise-grade MLOps ecosystem.

**Nota:** A vectorization layer (RAG com embeddings + busca vetorial) permanece mock nesta fase. O `search_context` continuará com resultados estáticos. A conexão com pgvector real fica para a Fase 3.

---

## 2. Tarefas (8/8)

| # | Tipo | Branch | Tarefa | Output |
|---|------|--------|--------|--------|
| D1 | `INF` | `INF/P2-D1` | Docker Compose com PostgreSQL 16 + pgvector. Configuração de conexão via env vars. ADR-003 para escolha de asyncpg. | docker-compose.yml funcional, `.env.example`, ADR-003 |
| D2 | `FET` | `FET/P2-D2` | Persistence layer base — `DatabaseManager` com pool asyncpg, health check, lifecycle. Schema de migrations (documents, audit_log). | Conexão ao DB funcional, schema criado |
| D3 | `FET` | `FET/P2-D3` | Core Context Layer — `CoreContextProvider` lendo dados reais (pyproject.toml, ruff.toml, filesystem). Resources `context://core/conventions` e `context://core/structure`. Replace do mock em `core_stack`. | 3 resources Core com dados reais |
| D4 | `FET` | `FET/P2-D4` | Decision Context Layer — parser de ADRs (.md → JSON). Resources `context://decisions/adrs` e `context://decisions/adrs/{id}` lendo do filesystem. | 2 resources Decision funcionais |
| D5 | `FET` | `FET/P2-D5` | Governance Model — `GovernanceService` com ciclo PROPOSED→APPROVED, `AuditLogger` persistindo no DB. Resource `context://governance/audit-log`. | Lifecycle funcional com audit |
| D6 | `FET` | `FET/P2-D6` | Workflow Context Layer — `WorkflowContextProvider` gerenciando contexto ativo. Resource `context://workflow/current`. | Workflow context funcional |
| D7 | `FET` | `FET/P2-D7` | Tool `register_adr` — cria ADR no filesystem + persiste metadados no DB. Registro no ToolExecutor. | Tool funcional via MCP |
| D8 | `TST` | `TST/P2-D8` | Testes de integração com DB real via Docker. Atualizar README e CHANGELOG. | Suite de integração, docs atualizados |

---

## 3. Dependências

| Tarefa | Depende de |
|--------|------------|
| D2 (Persistence) | D1 (Docker + DB) |
| D3 (Core Context) | D1 (config DB disponível, mas Core lê do filesystem) |
| D4 (Decision Context) | D1 (filesystem, independente de DB) |
| D5 (Governance) | D2 (Persistence layer para audit_log) |
| D6 (Workflow) | D5 (Governance para audit de transições) |
| D7 (register_adr) | D2 (Persistence), D4 (Decision Context) |
| D8 (Testes + Docs) | D1–D7 |

**Grafo de dependências:**

```
[D1] Docker + PostgreSQL
 ├──→ [D2] Persistence Layer
 │     ├──→ [D5] Governance ──→ [D6] Workflow
 │     └──→ [D7] register_adr
 ├──→ [D3] Core Context (filesystem, independente)
 └──→ [D4] Decision Context (filesystem, independente)
                                        └──→ [D7] register_adr
 [D1–D7] ──→ [D8] Testes + Docs
```

---

## 4. Outputs Esperados

| Artefato | Localização |
|----------|-------------|
| Docker Compose | `docker-compose.yml` |
| Env vars example | `.env.example` |
| ADR-003 | `docs/adr/ADR-003-asyncpg-driver.md` |
| DatabaseManager | `src/atlas_mcp/persistence/database.py` |
| Migrations | `src/atlas_mcp/persistence/migrations.py` |
| CoreContextProvider | `src/atlas_mcp/context/core.py` |
| Resource core/conventions | `src/atlas_mcp/resources/core_conventions.py` |
| Resource core/structure | `src/atlas_mcp/resources/core_structure.py` |
| DecisionContextProvider | `src/atlas_mcp/context/decision.py` |
| Resource decisions/adrs | `src/atlas_mcp/resources/decision_adrs.py` |
| GovernanceService | `src/atlas_mcp/governance/service.py` |
| AuditLogger | `src/atlas_mcp/governance/audit.py` |
| Resource governance/audit-log | `src/atlas_mcp/resources/governance_audit.py` |
| WorkflowContextProvider | `src/atlas_mcp/context/workflow.py` |
| Resource workflow/current | `src/atlas_mcp/resources/workflow_current.py` |
| Tool register_adr | `src/atlas_mcp/tools/register_adr.py` |
| Testes de integração | `tests/integration/` |

### Estrutura de diretórios esperada (novos arquivos):

```
Atlas-MCP/
├── docker-compose.yml
├── .env.example
├── src/atlas_mcp/
│   ├── context/
│   │   ├── __init__.py
│   │   ├── core.py              # CoreContextProvider
│   │   ├── decision.py          # DecisionContextProvider
│   │   └── workflow.py          # WorkflowContextProvider
│   ├── governance/
│   │   ├── __init__.py
│   │   ├── service.py           # GovernanceService
│   │   └── audit.py             # AuditLogger
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── database.py          # DatabaseManager
│   │   └── migrations.py        # Schema migrations
│   ├── resources/
│   │   ├── core_conventions.py  # context://core/conventions
│   │   ├── core_structure.py    # context://core/structure
│   │   ├── decision_adrs.py     # context://decisions/adrs[/{id}]
│   │   ├── governance_audit.py  # context://governance/audit-log
│   │   └── workflow_current.py  # context://workflow/current
│   └── tools/
│       └── register_adr.py      # Tool: register_adr
├── tests/
│   └── integration/
│       ├── conftest.py          # Fixtures com Docker DB
│       ├── test_persistence.py
│       └── test_governance.py
└── docs/
    └── adr/
        └── ADR-003-asyncpg-driver.md
```

---

## 5. Critérios de Validação

| # | Critério | Método de Verificação |
|---|----------|----------------------|
| 1 | `docker compose up -d` inicia PostgreSQL sem erro | Execução direta |
| 2 | `DatabaseManager` conecta e faz health check | Teste automatizado |
| 3 | Schema de migrations executa sem erro | Teste automatizado |
| 4 | `context://core/stack` retorna dados reais (não mock) | Teste automatizado + Inspector |
| 5 | `context://core/conventions` retorna convenções do projeto | Teste automatizado |
| 6 | `context://core/structure` retorna árvore de diretórios | Teste automatizado |
| 7 | `context://decisions/adrs` lista ADRs existentes | Teste automatizado |
| 8 | `context://decisions/adrs/001` retorna ADR-001 | Teste automatizado |
| 9 | `context://governance/audit-log` retorna entradas de audit | Teste automatizado |
| 10 | `context://workflow/current` retorna workflow ativo ou vazio | Teste automatizado |
| 11 | Tool `register_adr` cria arquivo .md e persiste no DB | Teste automatizado |
| 12 | `uv run pytest` — todos os testes passam | Execução da suite |
| 13 | `uv run mypy src/` — sem erros | Execução direta |
| 14 | Cobertura ≥ 80% mantida | pytest-cov |

---

## 6. Novas Dependências

| Pacote | Uso | Fase de Adição |
|--------|-----|----------------|
| `asyncpg` | Driver PostgreSQL async | D1 |
| `python-dotenv` | Leitura de `.env` | D1 |

---

## 7. Decisões Arquiteturais

| Decisão | Justificativa |
|---------|---------------|
| asyncpg em vez de psycopg3 | Async nativo, melhor performance com asyncio |
| Docker Compose para DB | Facilita dev local e CI |
| ADRs do filesystem primeiro | Produção usará DB; dev local lê .md |
| Sem vectorization nesta fase | Mocks do search_context permanecem; RAG real na Fase 3 |
| `plan_feature` e `analyze_bug` adiados | Dependem de workflow context maduro; Fase 3 |

---

## 8. Riscos da Fase

| Risco | Mitigação |
|-------|-----------|
| Docker não disponível em CI | Usar service containers no GitHub Actions |
| asyncpg incompatibilidade com pgvector | Testar extensão na D1 |
| Complexidade do governance model | Começar simples (D5), iterar |
| Parsing de ADRs .md frágil | Definir formato strict com regex testado |
