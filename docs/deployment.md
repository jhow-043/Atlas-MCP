# Guia de Deployment — Atlas MCP

Este documento cobre o deployment do Atlas MCP em ambientes de produção.

---

## Pré-requisitos

- Docker e Docker Compose v2
- Variáveis de ambiente configuradas (veja [configuração](configuration.md))
- API key do OpenAI (se usar embedding provider `openai`)

---

## Docker Compose (Recomendado)

### Startup básico

```bash
# Copiar variáveis de ambiente
cp .env.example .env
# Editar .env com valores de produção

# Subir todos os serviços
docker compose up -d

# Verificar saúde
docker compose ps
docker compose logs atlas-mcp --tail=20
```

### Serviços

| Serviço | Imagem | Porta | Descrição |
|---------|--------|-------|-----------|
| `postgres` | `pgvector/pgvector:pg16` | 5432 | PostgreSQL 16 + pgvector |
| `atlas-mcp` | Build local | — | Atlas MCP Server (stdio) |

### Configuração de Produção

Recomendações para o `docker-compose.yml` em produção:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    restart: always
    ports:
      - "127.0.0.1:5432:5432"  # Bind apenas em localhost
    environment:
      POSTGRES_USER: atlas_prod
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # Nunca commitar senhas
      POSTGRES_DB: atlas_mcp_prod
    volumes:
      - atlas_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U atlas_prod -d atlas_mcp_prod"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "1.0"

  atlas-mcp:
    build:
      context: .
      dockerfile: Dockerfile
    restart: always
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_USER: atlas_prod
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: atlas_mcp_prod
      EMBEDDING_PROVIDER: openai
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ATLAS_TRANSPORT: stdio
      ATLAS_LOG_LEVEL: INFO
      ATLAS_LOG_FORMAT: json  # JSON para ingestão por ferramentas
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "0.5"

volumes:
  atlas_data:
```

### Variáveis sensíveis

**Nunca** commite senhas ou API keys no repositório. Use:

```bash
# Arquivo .env (não versionado — está no .gitignore)
POSTGRES_PASSWORD=senha-segura-de-producao
OPENAI_API_KEY=sk-chave-real
```

Ou use secrets do Docker Compose / orquestrador.

---

## Health Checks

### PostgreSQL

```bash
# Via Docker
docker compose exec postgres pg_isready -U atlas -d atlas_mcp

# Via psql
docker compose exec postgres psql -U atlas -d atlas_mcp -c "SELECT 1;"
```

### Atlas MCP Server

```bash
# Verificar que o container está rodando
docker compose ps atlas-mcp

# Verificar logs no startup
docker compose logs atlas-mcp --tail=50

# Verificar que as migrações foram aplicadas
docker compose logs atlas-mcp | grep -i migration
```

### pgvector Extension

```bash
# Verificar que pgvector está instalado
docker compose exec postgres psql -U atlas -d atlas_mcp \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

---

## Backup e Restore

### Backup do PostgreSQL

```bash
# Backup completo (SQL dump)
docker compose exec postgres pg_dump -U atlas atlas_mcp > backup_$(date +%Y%m%d).sql

# Backup comprimido
docker compose exec postgres pg_dump -U atlas atlas_mcp | gzip > backup_$(date +%Y%m%d).sql.gz

# Backup apenas dos dados (sem schema)
docker compose exec postgres pg_dump -U atlas --data-only atlas_mcp > data_backup.sql
```

### Restore

```bash
# Restore de um backup
cat backup_20260223.sql | docker compose exec -T postgres psql -U atlas atlas_mcp

# Restore comprimido
gunzip -c backup_20260223.sql.gz | docker compose exec -T postgres psql -U atlas atlas_mcp
```

### Backup automático (cron)

```bash
# Adicionar ao crontab (backup diário às 02:00)
0 2 * * * cd /path/to/Atlas-MCP && docker compose exec -T postgres pg_dump -U atlas atlas_mcp | gzip > /backups/atlas_mcp_$(date +\%Y\%m\%d).sql.gz
```

---

## Atualização

### Atualizar o Atlas MCP

```bash
# Puxar alterações
git pull origin main

# Rebuild da imagem
docker compose build atlas-mcp

# Restart com zero downtime (PostgreSQL fica rodando)
docker compose up -d atlas-mcp

# Verificar que as migrações foram aplicadas
docker compose logs atlas-mcp --tail=20
```

> **Nota:** Migrações de banco são aplicadas automaticamente no startup do servidor. Não é necessário rodar manualmente.

### Atualizar o PostgreSQL

```bash
# ⚠️ Faça backup antes
docker compose exec postgres pg_dump -U atlas atlas_mcp > backup_pre_upgrade.sql

# Atualizar imagem no docker-compose.yml
# image: pgvector/pgvector:pg17  (quando disponível)

# Recrear container
docker compose up -d postgres
```

---

## Troubleshooting

### Servidor não conecta ao banco

**Sintoma:** Log com `connection refused` ou `could not connect to server`

**Solução:**
1. Verificar que o PostgreSQL está rodando: `docker compose ps postgres`
2. Verificar health check: `docker compose exec postgres pg_isready`
3. Verificar variáveis de ambiente (POSTGRES_HOST deve ser `postgres` quando dentro do Docker Compose, `localhost` quando fora)

### Pool de conexões esgotado

**Sintoma:** Log com `too many connections` ou timeouts

**Solução:**
1. Aumentar `DB_MAX_POOL_SIZE` no `.env`
2. Aumentar `max_connections` no PostgreSQL:
   ```bash
   docker compose exec postgres psql -U atlas -c "SHOW max_connections;"
   # Se necessário, adicionar ao docker-compose.yml:
   # command: postgres -c max_connections=200
   ```

### Embedding provider indisponível

**Sintoma:** `search_context` retorna `SERVICE_UNAVAILABLE`

**Solução:**
1. **OpenAI:** Verificar `OPENAI_API_KEY` e conectividade à internet
2. **Sentence Transformers:** Verificar que o pacote está instalado (`uv sync --extra local-embeddings`)
3. Verificar logs: `docker compose logs atlas-mcp | grep -i embed`

### Migrações falham no startup

**Sintoma:** Log com `migration failed` ou `relation already exists`

**Solução:**
1. Verificar estado do banco: `docker compose exec postgres psql -U atlas -d atlas_mcp -c "SELECT * FROM schema_migrations;"`
2. Se necessário, recriar o banco (⚠️ perda de dados):
   ```bash
   docker compose down -v  # Remove volumes
   docker compose up -d    # Recria tudo
   ```

### Servidor não inicia (FileNotFoundError)

**Sintoma:** Container crasha com `FileNotFoundError: pyproject.toml`

**Solução:** O servidor precisa dos arquivos de projeto para resources como `context://core/stack`. Garantir que o Dockerfile copia os arquivos necessários.

### Memória insuficiente

**Sintoma:** Container é killed (OOMKilled)

**Solução:**
1. Aumentar limite de memória no `deploy.resources.limits`
2. Se usando Sentence Transformers localmente, o modelo carrega na memória (~80–420 MB dependendo do modelo)
3. Reduzir `DB_MAX_POOL_SIZE` para liberar conexões

---

## Monitoramento

### Logs

```bash
# Logs em tempo real
docker compose logs -f atlas-mcp

# Logs do PostgreSQL
docker compose logs -f postgres

# Filtrar por nível
docker compose logs atlas-mcp | grep -E "ERROR|CRITICAL"
```

### Formato JSON (produção)

Com `ATLAS_LOG_FORMAT=json`, os logs podem ser ingeridos por ferramentas como:
- **Loki** + Grafana
- **CloudWatch Logs**
- **Elasticsearch** + Kibana
- **Datadog**

Exemplo de log JSON:
```json
{"timestamp": "2026-02-23T10:30:00", "level": "INFO", "logger": "atlas_mcp.bootstrap", "message": "Database initialized", "pool_size": 10}
```

### Métricas do PostgreSQL

```bash
# Conexões ativas
docker compose exec postgres psql -U atlas -d atlas_mcp \
  -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'atlas_mcp';"

# Tamanho do banco
docker compose exec postgres psql -U atlas -d atlas_mcp \
  -c "SELECT pg_size_pretty(pg_database_size('atlas_mcp'));"

# Tamanho da tabela de chunks
docker compose exec postgres psql -U atlas -d atlas_mcp \
  -c "SELECT pg_size_pretty(pg_total_relation_size('chunks'));"
```
