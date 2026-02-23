# P1-D7 — Testes Unitários Abrangentes (Cobertura ≥ 80%)

## Objetivo

Consolidar e expandir a suíte de testes unitários para `ProtocolHandler`,
`ResourceRegistry`, `ToolExecutor` e módulos auxiliares, garantindo cobertura
≥ 80% e validação de edge cases identificados na revisão.

## Estado Atual

- **72 testes** existentes em 7 arquivos
- **100% de cobertura** de statements/branches
- Lacunas identificadas: edge cases, testes duplicados, fixture morta

## Escopo

### Testes novos — Prioridade Alta

| # | Módulo | Cenário |
|---|--------|---------|
| 1 | `search_context` | Filtro com chave inexistente → 0 resultados |
| 2 | `search_context` | Múltiplos filtros simultâneos |
| 3 | `search_context` | Case-insensitive filter (`"DECISION"` → match) |
| 4 | `search_context` | `filters={}` (dict vazio) → sem filtragem |
| 5 | `search_context` | `limit` negativo → isError |
| 6 | `search_context` | `limit` > total results → retorna todos |
| 7 | `handler` | Após init, server tem resources E tools registrados (sem mock) |

### Testes novos — Prioridade Média

| # | Módulo | Cenário |
|---|--------|---------|
| 8 | `errors` | Re-exports (INTERNAL_ERROR, etc.) importáveis |
| 9 | `errors` | `format_tool_error` com `details={}` |
| 10 | `errors` | `create_error_data` com data falsy (`0`, `""`) |
| 11 | `core_stack` | Campos individuais: runtime, sdk, package_manager, etc. |
| 12 | `search_context` | Query com caracteres especiais / unicode |
| 13 | `search_context` | Combinação filtro + threshold + limit simultâneos |
| 14 | `search_context` | Threshold exatamente no valor de um score mock |
| 15 | `server` | `create_server()` retorna instâncias distintas |

### Housekeeping

| # | Ação |
|---|------|
| 16 | Remover fixture `sample_query` de `conftest.py` (código morto) |
| 17 | Remover teste duplicado `test_should_have_configure_capabilities_method` de `test_capabilities.py` |
| 18 | Testar imports via `__init__.py` dos sub-pacotes |

## Arquivos Modificados

- `tests/unit/test_executor.py` — edge cases search_context
- `tests/unit/test_handler.py` — teste de efeito real (sem mock)
- `tests/unit/test_errors.py` — re-exports, falsy data
- `tests/unit/test_registry.py` — campos individuais core_stack
- `tests/unit/test_server.py` — instâncias distintas
- `tests/unit/test_capabilities.py` — remover teste duplicado
- `tests/conftest.py` — remover fixture morta

## Critérios de Aceitação

1. Todos os testes passam (`uv run pytest`)
2. Cobertura ≥ 80% (atualmente 100%)
3. `uv run ruff check .` e `uv run ruff format .` passam
4. `uv run mypy src/` passa
5. Zero testes duplicados
6. Zero fixtures não utilizadas
