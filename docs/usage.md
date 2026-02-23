# Guia de Uso — Atlas MCP

Este documento explica como usar o Atlas MCP com diferentes clientes MCP.

---

## Claude Desktop

### Configuração

Adicione o Atlas MCP ao seu arquivo de configuração do Claude Desktop:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`  
**Linux:** `~/.config/Claude/claude_desktop_config.json`

#### Com OpenAI (requer API key)

```json
{
  "mcpServers": {
    "atlas-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "atlas_mcp"],
      "cwd": "/caminho/para/Atlas-MCP",
      "env": {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "atlas",
        "POSTGRES_PASSWORD": "atlas_dev",
        "POSTGRES_DB": "atlas_mcp",
        "EMBEDDING_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-sua-chave-aqui",
        "ATLAS_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

#### Com Sentence Transformers (local, sem API key)

```json
{
  "mcpServers": {
    "atlas-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "atlas_mcp"],
      "cwd": "/caminho/para/Atlas-MCP",
      "env": {
        "POSTGRES_HOST": "localhost",
        "EMBEDDING_PROVIDER": "sentence-transformers",
        "ATLAS_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

#### Modo degradado (sem banco de dados)

```json
{
  "mcpServers": {
    "atlas-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "atlas_mcp"],
      "cwd": "/caminho/para/Atlas-MCP"
    }
  }
}
```

> No modo degradado, resources funcionam normalmente. Tools de RAG retornam erro informativo.

### Verificação

Após configurar, reinicie o Claude Desktop. O Atlas MCP deve aparecer na lista de servidores MCP com:
- **7 resources** disponíveis
- **4 tools** disponíveis

---

## MCP Inspector

O [MCP Inspector](https://github.com/modelcontextprotocol/inspector) é uma ferramenta de debug para servidores MCP.

### Instalação

```bash
npx @modelcontextprotocol/inspector
```

### Conexão com Atlas MCP

```bash
npx @modelcontextprotocol/inspector \
  --command "uv run python -m atlas_mcp" \
  --cwd /caminho/para/Atlas-MCP
```

### Operações no Inspector

1. **Resources → List** — lista os 7 resources disponíveis
2. **Resources → Read** — lê o conteúdo de um resource específico
3. **Tools → List** — lista as 4 tools disponíveis
4. **Tools → Call** — executa uma tool com parâmetros

---

## Exemplos de Uso por Resource

### `context://core/stack`

Retorna a stack tecnológica do projeto (dados reais do `pyproject.toml`):

```
Resource: context://core/stack

Resposta esperada:
{
  "language": "Python",
  "version": ">=3.12",
  "runtime": "asyncio",
  "dependencies": ["mcp", "asyncpg", "python-dotenv", "openai", "numpy"],
  "dev_tools": {"lint": "ruff", "format": "ruff", "typecheck": "mypy", "test": "pytest"},
  ...
}
```

### `context://core/conventions`

Retorna as convenções de código (dados reais do `ruff.toml`):

```
Resource: context://core/conventions

Resposta esperada:
{
  "style": {"line_length": 100, "indent": 4, "quotes": "double"},
  "naming": {"modules": "snake_case", "classes": "PascalCase", ...},
  ...
}
```

### `context://core/structure`

Retorna a árvore de diretórios do projeto:

```
Resource: context://core/structure

Resposta esperada:
Atlas-MCP/
├── src/atlas_mcp/
│   ├── __main__.py
│   ├── server.py
│   ├── bootstrap.py
│   ...
```

### `context://decisions/adrs`

Lista todos os ADRs registrados no projeto:

```
Resource: context://decisions/adrs

Resposta esperada:
[
  {"id": "001", "title": "Use Python MCP SDK", "status": "Accepted"},
  {"id": "002", "title": "uv Package Manager", "status": "Accepted"},
  ...
]
```

### `context://decisions/adrs/{id}`

Detalhes de um ADR específico (ex: `context://decisions/adrs/001`):

```
Resource: context://decisions/adrs/001

Resposta esperada:
{
  "id": "001",
  "title": "Use Python MCP SDK",
  "status": "Accepted",
  "context": "...",
  "decision": "...",
  "consequences": "..."
}
```

### `context://workflow/current`

Retorna o workflow de desenvolvimento ativo:

```
Resource: context://workflow/current

Resposta (sem workflow ativo):
{"active": false, "message": "No active workflow"}

Resposta (com workflow ativo):
{"active": true, "type": "feature", "title": "...", "tasks": [...]}
```

### `context://governance/audit-log`

Trail de auditoria de governança (requer PostgreSQL):

```
Resource: context://governance/audit-log

Resposta esperada:
[
  {"timestamp": "2026-02-23T10:30:00", "action": "status_change", "document_id": 1, ...},
  ...
]
```

---

## Exemplos de Uso por Tool

### `search_context` — Busca Semântica

Busca no contexto do projeto usando similaridade vetorial (requer PostgreSQL + embeddings).

**Chamada:**
```json
{
  "name": "search_context",
  "arguments": {
    "query": "como configurar o banco de dados PostgreSQL",
    "limit": 5,
    "similarity_threshold": 0.7
  }
}
```

**Resposta:**
```json
{
  "query": "como configurar o banco de dados PostgreSQL",
  "total_results": 3,
  "filters_applied": {},
  "similarity_threshold": 0.7,
  "results": [
    {
      "chunk_id": 1,
      "document_id": 1,
      "content": "## PostgreSQL Configuration\n...",
      "section_path": "docs > configuration > postgresql",
      "similarity": 0.92,
      "metadata": {}
    }
  ]
}
```

**Com filtros:**
```json
{
  "name": "search_context",
  "arguments": {
    "query": "decisões de arquitetura",
    "filters": {"type": "decision"},
    "limit": 3
  }
}
```

### `plan_feature` — Planejamento de Feature

Gera um plano estruturado para uma nova feature, enriquecido com contexto do projeto.

**Chamada:**
```json
{
  "name": "plan_feature",
  "arguments": {
    "title": "Sistema de Cache de Contexto",
    "description": "Implementar cache em memória com TTL para resources frequentemente acessados",
    "requirements": [
      "TTL configurável por resource",
      "Invalidação automática por mudança de arquivo",
      "Métricas de hit/miss"
    ],
    "constraints": [
      "Sem dependências externas de cache",
      "Thread-safe para uso com asyncio"
    ]
  }
}
```

**Resposta:**
```json
{
  "feature": {
    "title": "Sistema de Cache de Contexto",
    "description": "...",
    "requirements": ["..."],
    "constraints": ["..."]
  },
  "related_context": [
    {"content": "...", "similarity": 0.85}
  ],
  "context_available": true
}
```

### `analyze_bug` — Análise de Bug

Gera uma análise estruturada de um bug, com contexto do projeto.

**Chamada:**
```json
{
  "name": "analyze_bug",
  "arguments": {
    "title": "Resource retorna vazio intermitentemente",
    "description": "O resource context://core/stack às vezes retorna string vazia",
    "expected_behavior": "Deve sempre retornar a stack completa do projeto",
    "steps_to_reproduce": [
      "Iniciar o servidor",
      "Chamar context://core/stack repetidamente",
      "Observar respostas vazias esporádicas"
    ]
  }
}
```

**Resposta:**
```json
{
  "bug": {
    "title": "Resource retorna vazio intermitentemente",
    "description": "...",
    "expected_behavior": "...",
    "steps_to_reproduce": ["..."]
  },
  "related_context": [
    {"content": "...", "similarity": 0.78}
  ],
  "context_available": true
}
```

### `register_adr` — Registrar ADR

Cria e registra um novo Architecture Decision Record (requer PostgreSQL).

**Chamada:**
```json
{
  "name": "register_adr",
  "arguments": {
    "title": "Usar Redis para cache de contexto",
    "context": "Resources são lidos frequentemente e o I/O de disco é um gargalo",
    "decision": "Implementar cache em memória com TTL, sem dependência de Redis",
    "consequences": "Menor complexidade operacional, mas sem cache compartilhado entre instâncias",
    "alternatives_considered": [
      "Redis — rejeitado por adicionar dependência operacional",
      "Memcached — rejeitado pelo mesmo motivo"
    ],
    "tags": ["performance", "cache", "architecture"]
  }
}
```

**Resposta:**
```json
{
  "status": "created",
  "adr": {
    "id": 5,
    "title": "Usar Redis para cache de contexto",
    "status": "PROPOSED"
  }
}
```

---

## Cenários de Uso Comuns

### 1. Agente recebendo contexto antes de codar

```
Agente: "Preciso entender o projeto antes de implementar"
→ Lê context://core/stack (stack tecnológica)
→ Lê context://core/conventions (convenções de código)
→ Lê context://core/structure (estrutura de diretórios)
→ Agente está contextualizado para gerar código alinhado ao projeto
```

### 2. Agente planejando uma feature

```
Agente: "Vou planejar a implementação de X"
→ Chama plan_feature(title="X", description="...")
→ Recebe plano estruturado + contexto relacionado do RAG
→ Plano pode ser revisado antes da implementação
```

### 3. Agente investigando um bug

```
Agente: "Investigar por que Y está falhando"
→ Chama analyze_bug(title="Y falha", description="...")
→ Recebe análise com possíveis causas + código relacionado do RAG
→ Agente segue a investigação com contexto
```

### 4. Agente buscando decisões anteriores

```
Agente: "Já decidimos algo sobre banco de dados?"
→ Chama search_context(query="decisão banco de dados")
→ Recebe ADRs e documentos relacionados
→ Agente respeita decisões existentes
```

---

## Troubleshooting

### Tool retorna `SERVICE_UNAVAILABLE`

```json
{"error": true, "error_code": "SERVICE_UNAVAILABLE", "message": "search_context requires a configured RAG pipeline..."}
```

**Causa:** PostgreSQL não está rodando ou embeddings não estão configurados.  
**Solução:**
```bash
docker compose up -d postgres
# Verificar variáveis de ambiente (EMBEDDING_PROVIDER, OPENAI_API_KEY)
```

### Resource retorna dados vazios

**Causa:** O arquivo-fonte do resource pode estar ausente (ex: `pyproject.toml` deletado).  
**Solução:** Verificar que os arquivos do projeto existem no diretório de trabalho.

### Claude Desktop não detecta o servidor

**Causa:** Caminho incorreto no `cwd` ou `uv` não está no PATH.  
**Solução:**
1. Verificar caminho absoluto no `cwd`
2. Verificar que `uv` está instalado: `uv --version`
3. Reiniciar o Claude Desktop após salvar a configuração
