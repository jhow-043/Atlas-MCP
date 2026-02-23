# Guia de Configuração — Atlas MCP

Este documento detalha todas as opções de configuração do Atlas MCP.

---

## Variáveis de Ambiente

O Atlas MCP lê configurações de variáveis de ambiente com suporte a arquivo `.env`:

```bash
cp .env.example .env
# Editar .env conforme necessário
```

O arquivo `.env` é carregado automaticamente via `python-dotenv` no startup. Variáveis definidas diretamente no ambiente têm prioridade sobre o `.env`.

---

## PostgreSQL

O Atlas MCP usa PostgreSQL 16 com a extensão pgvector para armazenamento vetorial.

| Variável | Descrição | Default | Obrigatória |
|----------|-----------|---------|-------------|
| `POSTGRES_HOST` | Host do servidor PostgreSQL | `localhost` | Não |
| `POSTGRES_PORT` | Porta do PostgreSQL | `5432` | Não |
| `POSTGRES_USER` | Usuário de conexão | `atlas` | Não |
| `POSTGRES_PASSWORD` | Senha de conexão | `atlas_dev` | Não |
| `POSTGRES_DB` | Nome do banco de dados | `atlas_mcp` | Não |
| `DB_MIN_POOL_SIZE` | Tamanho mínimo do pool de conexões | `2` | Não |
| `DB_MAX_POOL_SIZE` | Tamanho máximo do pool de conexões | `10` | Não |

> **Nota:** O banco de dados é opcional. Sem ele, o servidor opera em **modo degradado**: resources funcionam normalmente, mas tools que dependem de RAG (`search_context`) retornam erro informativo.

### Exemplo: PostgreSQL local

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=atlas
POSTGRES_PASSWORD=atlas_dev
POSTGRES_DB=atlas_mcp
```

### Exemplo: PostgreSQL em produção

```env
POSTGRES_HOST=db.example.com
POSTGRES_PORT=5432
POSTGRES_USER=atlas_prod
POSTGRES_PASSWORD=<senha-segura>
POSTGRES_DB=atlas_mcp_prod
DB_MIN_POOL_SIZE=5
DB_MAX_POOL_SIZE=20
```

---

## Embeddings

O Atlas MCP suporta dois providers de embeddings para a busca semântica (RAG).

| Variável | Descrição | Default | Obrigatória |
|----------|-----------|---------|-------------|
| `EMBEDDING_PROVIDER` | Provider de embeddings | `openai` | Não |
| `EMBEDDING_MODEL` | Modelo de embeddings | (depende do provider) | Não |
| `EMBEDDING_DIMENSION` | Dimensão dos vetores | (depende do provider) | Não |
| `OPENAI_API_KEY` | API key do OpenAI | — | Se provider=`openai` |

### OpenAI (padrão)

Usa a API do OpenAI para gerar embeddings. Requer API key e conexão à internet.

```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=sk-sua-chave-aqui
```

**Modelos disponíveis:**

| Modelo | Dimensão | Custo | Qualidade |
|--------|----------|-------|-----------|
| `text-embedding-3-small` | 1536 | Baixo | Boa |
| `text-embedding-3-large` | 3072 | Médio | Excelente |
| `text-embedding-ada-002` | 1536 | Baixo | Boa |

### Sentence Transformers (local)

Roda localmente sem necessidade de API key ou internet. Ideal para desenvolvimento e ambientes offline.

```env
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
# OPENAI_API_KEY não é necessária
```

Para instalar o suporte a sentence-transformers:

```bash
uv sync --extra local-embeddings
```

**Modelos disponíveis:**

| Modelo | Dimensão | Tamanho | Qualidade |
|--------|----------|---------|-----------|
| `all-MiniLM-L6-v2` | 384 | 80 MB | Boa |
| `all-mpnet-base-v2` | 768 | 420 MB | Excelente |

> **Importante:** A dimensão configurada deve corresponder ao modelo escolhido. Se não especificada, o default correto é aplicado automaticamente.

---

## Servidor

| Variável | Descrição | Default | Obrigatória |
|----------|-----------|---------|-------------|
| `ATLAS_TRANSPORT` | Transporte MCP | `stdio` | Não |
| `ATLAS_SSE_HOST` | Host para transporte SSE | `0.0.0.0` | Não |
| `ATLAS_SSE_PORT` | Porta para transporte SSE | `8000` | Não |

### Transport: stdio (padrão)

Comunicação via stdin/stdout. Usado por clientes MCP como Claude Desktop.

```env
ATLAS_TRANSPORT=stdio
```

```bash
uv run python -m atlas_mcp
```

### Transport: SSE (HTTP)

Comunicação via Server-Sent Events sobre HTTP. Útil para integração com clientes web.

```env
ATLAS_TRANSPORT=sse
ATLAS_SSE_HOST=0.0.0.0
ATLAS_SSE_PORT=8000
```

```bash
uv run python -m atlas_mcp
# Servidor acessível em http://localhost:8000
```

---

## Logging

| Variável | Descrição | Default | Obrigatória |
|----------|-----------|---------|-------------|
| `ATLAS_LOG_LEVEL` | Nível mínimo de log | `INFO` | Não |
| `ATLAS_LOG_FORMAT` | Formato de saída | `text` | Não |

### Níveis de log

| Nível | Uso |
|-------|-----|
| `DEBUG` | Desenvolvimento — máximo detalhe |
| `INFO` | Produção — operações normais |
| `WARNING` | Situações inesperadas não-críticas |
| `ERROR` | Falhas que impedem uma operação |
| `CRITICAL` | Falhas que impedem o servidor |

### Formatos

**`text`** (padrão) — legível para desenvolvimento:
```
2026-02-23 10:30:00 [INFO] atlas_mcp.bootstrap: Database initialized
2026-02-23 10:30:01 [INFO] atlas_mcp.bootstrap: Migrations applied
```

**`json`** — estruturado para ingestão por ferramentas (Loki, CloudWatch, etc):
```json
{"timestamp": "2026-02-23T10:30:00", "level": "INFO", "logger": "atlas_mcp.bootstrap", "message": "Database initialized"}
```

> **Nota:** Logs são emitidos no stderr para não interferir com o transporte stdio do MCP.

---

## Modo Degradado

O Atlas MCP funciona mesmo sem PostgreSQL disponível:

| Funcionalidade | Com DB | Sem DB |
|----------------|--------|--------|
| Resources (`context://core/*`) | ✅ | ✅ |
| Resources (`context://decisions/*`) | ✅ | ✅ |
| Resources (`context://workflow/*`) | ✅ | ✅ |
| Resources (`context://governance/*`) | ⚠️ Vazio | ⚠️ Vazio |
| Tool `search_context` | ✅ RAG real | ❌ Erro informativo |
| Tool `plan_feature` | ✅ Com contexto | ✅ Sem contexto |
| Tool `analyze_bug` | ✅ Com contexto | ✅ Sem contexto |
| Tool `register_adr` | ✅ Persiste | ❌ Erro informativo |

Para rodar em modo degradado (desenvolvimento sem Docker):

```bash
# Sem variáveis de DB — servidor detecta automaticamente
uv run python -m atlas_mcp
```

---

## Configuração Completa de Referência

```env
# ── PostgreSQL ───────────────────────────────────────────
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=atlas
POSTGRES_PASSWORD=atlas_dev
POSTGRES_DB=atlas_mcp
# DB_MIN_POOL_SIZE=2
# DB_MAX_POOL_SIZE=10

# ── Embeddings ───────────────────────────────────────────
EMBEDDING_PROVIDER=openai
# EMBEDDING_MODEL=text-embedding-3-small
# EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=sk-sua-chave-aqui

# ── Servidor ─────────────────────────────────────────────
ATLAS_TRANSPORT=stdio
# ATLAS_SSE_HOST=0.0.0.0
# ATLAS_SSE_PORT=8000

# ── Logging ──────────────────────────────────────────────
ATLAS_LOG_LEVEL=INFO
ATLAS_LOG_FORMAT=text
```
