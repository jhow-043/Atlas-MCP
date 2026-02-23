# P2-D1 — Docker Compose + PostgreSQL 16 + pgvector

## Objetivo

Configurar a infraestrutura de banco de dados para o Atlas MCP usando Docker
Compose com PostgreSQL 16 + extensão pgvector. Adicionar dependências de
runtime (asyncpg) e documentar a decisão via ADR-003.

## Escopo

| Item | Descrição |
|------|-----------|
| `docker-compose.yml` | PostgreSQL 16 com pgvector, healthcheck, volume persistente |
| `.env.example` | Variáveis de ambiente para conexão |
| `persistence/config.py` | Configuração de conexão lida de env vars |
| `ADR-003` | Decisão de usar asyncpg como driver |
| `pyproject.toml` | Adicionar asyncpg e python-dotenv |
| `.gitignore` | Ignorar `.env` |

## Arquivos

### Novos
- `docker-compose.yml`
- `.env.example`
- `src/atlas_mcp/persistence/config.py`
- `docs/adr/ADR-003-asyncpg-driver.md`
- `docs/tasks/P2-D1-planning.md`
- `tests/unit/test_persistence_config.py`

### Modificados
- `pyproject.toml` — novas dependências
- `.gitignore` — adicionar `.env`

## Critérios de Aceitação

1. `docker compose up -d` inicia container sem erro
2. `pg_isready` retorna OK no healthcheck
3. Configuração lê variáveis de ambiente corretamente
4. Fallback para valores default funciona
5. Todos os testes passam
6. ADR-003 documentado
