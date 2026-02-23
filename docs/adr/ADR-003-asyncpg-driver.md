# ADR-003 — Uso de asyncpg como Driver PostgreSQL

## Status

APPROVED

## Data

2026-02-23

## Contexto

O Atlas MCP precisa de um driver PostgreSQL para a persistence layer.
O servidor é inteiramente assíncrono (asyncio), e o driver deve ser
compatível com o runtime sem bloquear a event loop.

Opções consideradas:

1. **asyncpg** — driver PostgreSQL async nativo, escrito em Cython,
   protocolo binário PostgreSQL.
2. **psycopg 3** — wrapper async sobre libpq, suporta sync e async.
3. **databases + encode** — abstração multi-driver.

## Decisão

Utilizar **asyncpg** como driver PostgreSQL.

## Justificativa

- **Performance:** asyncpg é o driver async mais rápido para PostgreSQL,
  usando protocolo binário nativo em vez de libpq.
- **Async nativo:** não depende de thread pool — async de verdade.
- **Compatibilidade com pgvector:** a extensão `pgvector` funciona com
  asyncpg via queries SQL padrão (`CREATE EXTENSION`, tipos `vector`).
- **Maturidade:** amplamente adotado em projetos asyncio de produção
  (FastAPI, Starlette, etc.).
- **Connection pool:** pool integrado via `asyncpg.create_pool()` com
  configuração declarativa (min/max size, timeout).
- **Sinergia com o stack:** Python ≥ 3.12 + asyncio + FastMCP — tudo
  async, sem adapter sync→async.

## Consequências

- Não é possível usar ORMs tradicionais (SQLAlchemy async requer
  a extensão greenlet); queries são SQL puro.
- Migrations manuais (ou com ferramenta leve) em vez de Alembic.
- O tipo `vector` do pgvector é mapeado manualmente via `asyncpg`
  type codecs (necessário a partir da Fase 3).

## Alternativas Descartadas

- **psycopg 3:** Bom suporte async, mas depende de libpq e thread pool
  para o modo async. Performance inferior ao asyncpg em benchmarks.
- **databases:** Abstração desnecessária para um projeto que usa
  exclusivamente PostgreSQL. Camada extra sem benefício.
