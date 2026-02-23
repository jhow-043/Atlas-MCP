# P2-D2 — Persistence Layer Base

**Tipo:** `FET`  
**Branch:** `FET/P2-D2`  
**Depende de:** D1 (Docker + DB config)

---

## Objetivo

Implementar a camada de persistência base com `DatabaseManager` (pool asyncpg, lifecycle, health check) e schema de migrations (tabelas `documents`, `audit_log`).

## Artefatos

| Arquivo | Descrição |
|---------|-----------|
| `src/atlas_mcp/persistence/database.py` | `DatabaseManager` — connection pool, init/close, health check |
| `src/atlas_mcp/persistence/migrations.py` | Schema SQL + `MigrationRunner` |
| `tests/unit/test_database.py` | Testes unitários com mock do asyncpg |
| `tests/unit/test_migrations.py` | Testes unitários do schema/migrations |
| `docs/tasks/P2-D2-planning.md` | Este documento |

## Design

### DatabaseManager

- `__init__(config: DatabaseConfig)` — recebe config
- `async initialize()` — cria pool asyncpg
- `async close()` — fecha pool
- `async health_check() -> dict` — verifica conexão
- `async execute(query, *args)` — executa query
- `async fetch(query, *args)` — retorna records
- `async fetchrow(query, *args)` — retorna single record
- Context manager (`__aenter__`/`__aexit__`) para lifecycle

### Schema (tables)

```sql
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PROPOSED',
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Critérios de Validação

1. `DatabaseManager` testável com mocks (sem DB real nos unit tests)
2. Schema SQL definido e versionado
3. `MigrationRunner` capaz de executar migrations em sequência
4. Todos os testes passam, cobertura ≥ 80%
5. mypy, ruff check, ruff format sem erros
