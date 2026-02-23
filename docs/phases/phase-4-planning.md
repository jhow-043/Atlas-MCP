# Fase 4 — Bootstrap, Wiring e Servidor Funcional

**Status:** APROVADO  
**Data:** 2026-02-23  
**Versão:** 2.0  
**Repositório:** `https://github.com/jhow-043/Atlas-MCP.git`

---

## 1. Objetivo da Fase

Conectar todos os módulos das Fases 1–3 num **startup real** e validar o servidor de ponta a ponta com banco de dados rodando no Docker. Ao final:

- Subir o PostgreSQL + pgvector via `docker compose up -d`
- Rodar `uv run python -m atlas_mcp` e ter o servidor funcional com RAG completo
- Validar todo o fluxo via MCP Inspector (resources, tools, search_context com resultados reais)
- Testes de integração reais contra o banco

Foco 100% em **fazer funcionar**. Documentação final fica para a Fase 5.

---

## 2. Tarefas (8/8)

| # | Tipo | Branch | Tarefa | Output |
|---|------|--------|--------|--------|
| D1 | `FET` | `FET/P4-D1` | Implementar `Settings` — dataclass centralizada que unifica `DatabaseConfig` + provider de embeddings (tipo, modelo, API key, dimensão) + transport (stdio/sse) + log level/format. Lê `.env` via `python-dotenv`. Atualizar `.env.example` com todas as variáveis. | `src/atlas_mcp/config/settings.py` + `.env.example` atualizado |
| D2 | `FET` | `FET/P4-D2` | Implementar logging estruturado — `setup_logging(level, fmt)` configura `logging.basicConfig` com formato legível (dev) ou JSON (prod). Logs no stderr para não poluir stdio do MCP. | `src/atlas_mcp/config/logging.py` |
| D3 | `FET` | `FET/P4-D3` | Implementar `ApplicationBootstrap` — classe async que faz o wiring completo: `Settings` → `DatabaseManager.initialize()` → `MigrationRunner.run()` → `register_vector_codec()` → instanciar `EmbeddingProvider` + `VectorStore` + `IndexingService` → `configure()` em `search_context`, `plan_feature`, `analyze_bug` → `GovernanceService.register_on_status_change(indexing.on_status_change)`. Expõe `shutdown()` para fechar pool. | `src/atlas_mcp/bootstrap.py` |
| D4 | `FET` | `FET/P4-D4` | Reescrever `__main__.py` — integrar `Settings.from_env()`, `setup_logging()`, `ApplicationBootstrap.startup()` + `ProtocolHandler.run()`. Suportar flag `--transport stdio\|sse`. Graceful shutdown com `try/finally` + signal handlers (SIGTERM/SIGINT). Funcionar também sem DB (modo degradado: resources ok, RAG indisponível). | `__main__.py` funcional |
| D5 | `TST` | `TST/P4-D5` | Testes unitários: `TestSettings` (env vars, defaults, validação), `TestSetupLogging` (níveis, formatos), `TestApplicationBootstrap` (com mocks — startup configura tudo, shutdown fecha pool), `TestMain` (arg parsing, modo degradado). | `tests/unit/test_settings.py`, `test_logging_setup.py`, `test_bootstrap.py`, `test_main.py` |
| D6 | `TST` | `TST/P4-D6` | Testes de integração **reais com PostgreSQL**: subir DB via Docker, rodar migrações, testar pipeline completo: indexar documento → `search_context` retorna resultados → `plan_feature`/`analyze_bug` retornam contexto. Testar `GovernanceService.transition()` dispara indexação. Marker `@pytest.mark.integration`. | `tests/integration/test_full_pipeline.py` |
| D7 | `TST` | `TST/P4-D7` | Smoke test do servidor: subir o servidor real via subprocess, conectar como client MCP via SDK, chamar `resources/list`, `tools/list`, `tools/call` com `search_context`, verificar que responde corretamente. | `tests/integration/test_server_smoke.py` |
| D8 | `INF` | `INF/P4-D8` | Criar `Dockerfile` multi-stage para o servidor. Atualizar `docker-compose.yml` com serviço `atlas-mcp` (build, depends_on postgres, health check, env vars). `docker compose up` sobe tudo. | `Dockerfile` + `docker-compose.yml` atualizado |

---

## 3. Dependências

| Tarefa | Depende de |
|--------|------------|
| D1 (Settings) | — |
| D2 (Logging) | — |
| D3 (Bootstrap) | D1 |
| D4 (__main__.py) | D1, D2, D3 |
| D5 (Testes unitários) | D1, D2, D3, D4 |
| D6 (Testes integração) | D4 + Docker rodando |
| D7 (Smoke test) | D4 |
| D8 (Docker image) | D4 |

**Grafo:**

```
[D1] Settings ──→ [D3] Bootstrap ──→ [D4] __main__.py ──→ [D5] Testes unit
[D2] Logging ─────────────────────→ [D4]               ──→ [D6] Testes integração
                                                        ──→ [D7] Smoke test
                                                        ──→ [D8] Dockerfile + Compose
```

---

## 4. Outputs Esperados

| Artefato | Localização |
|----------|-------------|
| Settings | `src/atlas_mcp/config/settings.py` |
| Logging setup | `src/atlas_mcp/config/logging.py` |
| Config __init__ | `src/atlas_mcp/config/__init__.py` |
| ApplicationBootstrap | `src/atlas_mcp/bootstrap.py` |
| Entry point (reescrito) | `src/atlas_mcp/__main__.py` |
| .env.example (atualizado) | `.env.example` |
| Dockerfile | `Dockerfile` |
| Docker Compose (atualizado) | `docker-compose.yml` |
| Testes unitários | `tests/unit/test_settings.py`, `test_logging_setup.py`, `test_bootstrap.py`, `test_main.py` |
| Testes integração | `tests/integration/test_full_pipeline.py` |
| Smoke test | `tests/integration/test_server_smoke.py` |

---

## 5. Detalhamento Técnico

### D1 — Settings

Unifica todas as configurações em um único ponto:

- Lê `.env` via `dotenv.load_dotenv()` antes de `os.environ.get()`
- Compõe `DatabaseConfig.from_env()` internamente
- Novas variáveis: `EMBEDDING_PROVIDER` (`openai`|`sentence-transformers`), `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, `OPENAI_API_KEY`, `ATLAS_TRANSPORT` (`stdio`|`sse`), `ATLAS_SSE_HOST`, `ATLAS_SSE_PORT`, `ATLAS_LOG_LEVEL`, `ATLAS_LOG_FORMAT`

### D3 — ApplicationBootstrap

Sequência de startup:

1. `DatabaseConfig` → `DatabaseManager(config)` → `await db.initialize()`
2. `await MigrationRunner(db).run()` (aplica migrations pendentes)
3. `register_vector_codec` no pool (via `pool.acquire()`)
4. Instanciar `EmbeddingProvider` (OpenAI ou SentenceTransformer conforme settings)
5. Instanciar `VectorStore(db)` + `MarkdownChunker()` + `IndexingService(chunker, embedder, store)`
6. `search_context.configure(embedder, store)` + `plan_feature.configure(embedder, store)` + `analyze_bug.configure(embedder, store)`
7. `GovernanceService(db, AuditLogger(db)).register_on_status_change(indexing.on_status_change)`

Modo degradado (DB indisponível):
- Loga warning, não crasha
- Resources funcionam normalmente
- Tools RAG retornam erro claro ("serviço indisponível")

### D4 — __main__.py

- `Settings.from_env()` → `setup_logging()` → `ApplicationBootstrap.startup()` → `ProtocolHandler.run(transport=settings.transport)`
- `try/finally` garante `bootstrap.shutdown()`
- Se DB falha no startup → modo degradado, servidor roda com resources + register_adr

### D6 — Testes integração reais

Pré-requisito: `docker compose up -d` com PostgreSQL rodando. Testes marcados com `@pytest.mark.integration`, skip automático se DB indisponível.

### D7 — Smoke test

- Sobe `python -m atlas_mcp` como subprocess
- Conecta via MCP client SDK (stdio transport)
- Chama `initialize` → `resources/list` → `tools/list` → `tools/call search_context`
- Valida respostas JSON-RPC

---

## 6. Critérios de Validação

| # | Critério | Método |
|---|----------|--------|
| 1 | `docker compose up -d` sobe PostgreSQL saudável | `docker compose ps` |
| 2 | `uv run python -m atlas_mcp` conecta no DB e roda migrações | Log no stderr |
| 3 | MCP Inspector lista 6 resources e 4 tools | Inspector manual |
| 4 | `search_context` retorna resultados reais do pgvector | Inspector + teste |
| 5 | `plan_feature` e `analyze_bug` retornam `context_available: true` | Inspector + teste |
| 6 | Servidor funciona sem DB (modo degradado) | Teste unitário + manual |
| 7 | Ctrl+C faz shutdown limpo (pool fechado, sem warnings) | Manual |
| 8 | `docker compose up` sobe server + DB juntos | Execução direta |
| 9 | `uv run pytest` passa (unit + integration quando DB disponível) | CI |
| 10 | `ruff check`, `ruff format --check`, `mypy src/` passam | CI |

---

## 7. Riscos

| Risco | Mitigação |
|-------|-----------|
| FastMCP `run()` é bloqueante, conflita com bootstrap async | SSE usa internamente asyncio; stdio pode precisar de `asyncio.run()` wrapper. Testar cedo em D4. |
| `register_vector_codec` precisa de connection, não pool | Usar `async with pool.acquire() as conn` para registrar o codec. |
| Testes de integração lentos na CI | Separar com marker `integration`, rodar só quando DB disponível. |
| OpenAI API key necessária | Suportar SentenceTransformers como fallback local. |

---

## 8. Observações

- Esta fase **não** adiciona novas tools ou resources — foco é wiring e validação.
- O `config/` é um novo pacote; não substitui `persistence/config.py`.
- A documentação (README completo, Getting Started, CHANGELOG) fica para a **Fase 5**.
- Após esta fase: `docker compose up -d` + `uv run python -m atlas_mcp` = servidor pronto para uso.
