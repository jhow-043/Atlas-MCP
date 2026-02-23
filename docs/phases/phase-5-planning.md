# Fase 5 — Documentação, Hardening e Release v0.1.0

**Status:** PROPOSTO  
**Data:** 2026-02-23  
**Versão:** 1.0  
**Repositório:** `https://github.com/jhow-043/Atlas-MCP.git`

---

## 1. Objetivo da Fase

Preparar o Atlas MCP para a primeira release pública (`v0.1.0`). Ao final:

- Documentação profissional e completa (README, CONTRIBUTING, guias)
- Exemplos de configuração para Claude Desktop e MCP Inspector
- Inputs validados robustamente em todas as tools
- CHANGELOG atualizado com todas as fases (0–4)
- Versão `0.1.0` no `pyproject.toml`, tag e release notes
- Projeto pronto para ser consumido por usuários externos

Foco 100% em **documentação, polish e release**. Sem novas tools ou resources.

---

## 2. Contexto

### Gerado via Atlas MCP

Este planejamento foi construído usando as tools do próprio Atlas MCP:

- **`plan_feature`** — gerou a estrutura base do plano com requisitos e constraints
- **`analyze_bug`** — identificou áreas de hardening necessárias (validação de inputs, graceful degradation, error messages)
- **Resources `context://core/*`** — forneceram stack, convenções e estrutura atuais
- **Resource `context://workflow/current`** — confirmou que nenhuma fase estava ativa

### Estado Atual (pós-Fase 4)

| Métrica | Valor |
|---------|-------|
| Testes | 510+ |
| Cobertura | 96% |
| Tools MCP | 4 (`search_context`, `plan_feature`, `analyze_bug`, `register_adr`) |
| Resources MCP | 7 (3 core + 2 decisions + 1 governance + 1 workflow) |
| Transports | stdio (SSE preparado mas não validado) |
| Infraestrutura | Dockerfile + docker-compose (PostgreSQL 16 + pgvector) |

### Lacunas identificadas

1. **README desatualizado** — tabela de status para na Fase 2, tools listam `search_context` como "mock"
2. **CHANGELOG incompleto** — Fases 3 e 4 estão no `[Unreleased]` mas sem separação por release
3. **CONTRIBUTING.md** — falta setup com Docker, como rodar testes de integração
4. **Sem guia de deployment** — usuário não sabe como configurar em produção
5. **Sem exemplos de uso** — falta `claude_desktop_config.json`, snippets de MCP Inspector
6. **Validação de inputs fraca** — tools aceitam valores fora de range sem validação
7. **Versão** — `pyproject.toml` ainda em `0.0.1`

---

## 3. Tarefas (8/8)

| # | Tipo | Branch | Tarefa | Output |
|---|------|--------|--------|--------|
| D1 | `DOC` | `DOC/P5-D1` | Reescrever `README.md` — badges atualizados (CI, coverage, license, Python), descrição clara, tabela de status com Fases 0–4. Quick Start com dois caminhos: stdio local (`uv run python -m atlas_mcp`) e Docker (`docker compose up`). Seção de Resources e Tools atualizada com as 4 tools reais. Arquitetura resumida com diagrama. Links para docs de configuração e contribuição. | `README.md` reescrito |
| D2 | `DOC` | `DOC/P5-D2` | Criar guia de configuração `docs/configuration.md` — documentar todas as variáveis de ambiente (`.env`), modos de embedding (OpenAI vs Sentence Transformers local), transports (stdio vs SSE), configuração do banco de dados. Incluir `.env.example` comentado. Documentar modo degradado (sem DB). | `docs/configuration.md` + `.env.example` atualizado |
| D3 | `DOC` | `DOC/P5-D3` | Criar guia de uso `docs/usage.md` — configuração para Claude Desktop (`claude_desktop_config.json`), uso com MCP Inspector, exemplos de chamadas reais para cada tool e resource. Incluir screenshots ou outputs esperados. | `docs/usage.md` |
| D4 | `DOC` | `DOC/P5-D4` | Atualizar `CONTRIBUTING.md` com fluxo completo — setup com Docker (`docker compose up -d`), como rodar testes unitários e de integração, como adicionar uma nova tool/resource, checklist de PR. Atualizar `CHANGELOG.md` — mover conteúdo de `[Unreleased]` para seção `[0.1.0]`, adicionar entradas das Fases 3 e 4 que faltam. | `CONTRIBUTING.md` + `CHANGELOG.md` atualizados |
| D5 | `DOC` | `DOC/P5-D5` | Criar guia de deployment `docs/deployment.md` — Docker Compose em produção (volumes, restart policies, resource limits), health checks, backup do PostgreSQL, troubleshooting de problemas comuns (pool exhausted, embedding provider down, migration failures). | `docs/deployment.md` |
| D6 | `FET` | `FET/P5-D6` | Hardening de validação nas tools — implementar validação robusta de inputs em `search_context` (query não vazia, `0 < similarity_threshold ≤ 1`, `limit > 0`), `plan_feature` (title obrigatório, description não vazia), `analyze_bug` (title obrigatório), `register_adr` (title, context, decision obrigatórios). Retornar `InvalidParams` com mensagens claras e acionáveis. | Tools com validação robusta |
| D7 | `TST` | `TST/P5-D7` | Testes de hardening — testar todos os edge cases de validação: inputs vazios, valores fora de range, tipos incorretos, strings extremamente longas. Testar error messages retornadas. Garantir que nenhum input malformado cause crash. | `tests/unit/test_tool_validation.py` |
| D8 | `INF` | `INF/P5-D8` | Preparação de release v0.1.0 — atualizar `version` no `pyproject.toml` para `0.1.0`, atualizar `Development Status` para `3 - Alpha`, criar tag `v0.1.0`, escrever release notes. Verificar que todos os checks passam (ruff, mypy, pytest). | `pyproject.toml` atualizado + tag `v0.1.0` |

---

## 4. Dependências

| Tarefa | Depende de |
|--------|------------|
| D1 (README) | — |
| D2 (Configuração) | — |
| D3 (Uso) | D2 (referencia config) |
| D4 (Contributing + Changelog) | — |
| D5 (Deployment) | D2 (referencia config) |
| D6 (Hardening) | — |
| D7 (Testes hardening) | D6 |
| D8 (Release) | D1, D2, D3, D4, D5, D6, D7 |

**Grafo:**

```
[D1] README ─────────────────────────────────────────→ [D8] Release v0.1.0
[D2] Configuração ──→ [D3] Uso ──────────────────────→ [D8]
                  ──→ [D5] Deployment ───────────────→ [D8]
[D4] Contributing + Changelog ───────────────────────→ [D8]
[D6] Hardening ──→ [D7] Testes hardening ────────────→ [D8]
```

---

## 5. Outputs Esperados

| Artefato | Localização |
|----------|-------------|
| README (reescrito) | `README.md` |
| Guia de Configuração | `docs/configuration.md` |
| Guia de Uso | `docs/usage.md` |
| Guia de Deployment | `docs/deployment.md` |
| .env.example (atualizado) | `.env.example` |
| Contributing (atualizado) | `CONTRIBUTING.md` |
| Changelog (atualizado) | `CHANGELOG.md` |
| Tools com validação | `src/atlas_mcp/tools/*.py` |
| Testes de validação | `tests/unit/test_tool_validation.py` |
| pyproject.toml (v0.1.0) | `pyproject.toml` |

---

## 6. Detalhamento Técnico

### D1 — README.md

Estrutura alvo:

```
# Atlas MCP
[badges]
[descrição + valor prop]
## Status do Projeto (tabela Fases 0–4)
## Quick Start
  ### Opção 1: Docker (recomendado)
  ### Opção 2: Local (stdio)
## Resources
## Tools
## Arquitetura (diagrama simplificado)
## Configuração → link para docs/configuration.md
## Uso → link para docs/usage.md
## Deployment → link para docs/deployment.md
## Contribuição → link para CONTRIBUTING.md
## License
```

### D2 — Guia de Configuração

Documentar cada variável de ambiente:

| Variável | Descrição | Default | Obrigatória |
|----------|-----------|---------|-------------|
| `ATLAS_DB_HOST` | Host do PostgreSQL | `localhost` | Não |
| `ATLAS_DB_PORT` | Porta do PostgreSQL | `5432` | Não |
| `ATLAS_DB_NAME` | Nome do banco | `atlas_mcp` | Não |
| `ATLAS_DB_USER` | Usuário do banco | `atlas` | Não |
| `ATLAS_DB_PASSWORD` | Senha do banco | `atlas` | Não |
| `EMBEDDING_PROVIDER` | Provider de embeddings | `openai` | Não |
| `EMBEDDING_MODEL` | Modelo de embeddings | (provider default) | Não |
| `EMBEDDING_DIMENSION` | Dimensão dos vetores | (modelo default) | Não |
| `OPENAI_API_KEY` | API key do OpenAI | — | Se provider=openai |
| `ATLAS_TRANSPORT` | Transport MCP | `stdio` | Não |
| `ATLAS_LOG_LEVEL` | Nível de log | `INFO` | Não |
| `ATLAS_LOG_FORMAT` | Formato de log | `text` | Não |

### D3 — Guia de Uso

Exemplo de `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "atlas-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "atlas_mcp"],
      "cwd": "/path/to/Atlas-MCP",
      "env": {
        "ATLAS_DB_HOST": "localhost",
        "EMBEDDING_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

### D6 — Hardening

Validações a implementar:

```python
# search_context
if not query or not query.strip():
    raise InvalidParams("query cannot be empty")
if similarity_threshold is not None and not (0 < similarity_threshold <= 1):
    raise InvalidParams("similarity_threshold must be between 0 (exclusive) and 1 (inclusive)")
if limit is not None and limit < 1:
    raise InvalidParams("limit must be a positive integer")

# plan_feature
if not title or not title.strip():
    raise InvalidParams("title is required")
if not description or not description.strip():
    raise InvalidParams("description is required")

# analyze_bug
if not title or not title.strip():
    raise InvalidParams("title is required")
if not description or not description.strip():
    raise InvalidParams("description is required")

# register_adr
if not title or not title.strip():
    raise InvalidParams("title is required")
if not context or not context.strip():
    raise InvalidParams("context is required")
if not decision or not decision.strip():
    raise InvalidParams("decision is required")
```

---

## 7. Critérios de Validação

| # | Critério | Método |
|---|----------|--------|
| 1 | README contém Quick Start funcional (stdio + Docker) | Revisão manual |
| 2 | Todas as env vars documentadas em `docs/configuration.md` | Revisão + diff com Settings |
| 3 | `claude_desktop_config.json` funciona com Claude Desktop | Teste manual |
| 4 | CHANGELOG tem entradas para Fases 0–4 + release `[0.1.0]` | Revisão |
| 5 | CONTRIBUTING explica setup com Docker e testes de integração | Revisão |
| 6 | `docs/deployment.md` cobre Docker Compose em produção | Revisão |
| 7 | Tools rejeitam inputs inválidos com `InvalidParams` claro | Testes automatizados |
| 8 | Nenhum input malformado causa crash do servidor | Testes automatizados |
| 9 | `pyproject.toml` com version `0.1.0` e status `Alpha` | Revisão |
| 10 | `ruff check`, `ruff format --check`, `mypy src/`, `pytest` passam | CI |

---

## 8. Riscos

| Risco | Mitigação |
|-------|-----------|
| Documentação fica desatualizada rapidamente | Usar dados dinâmicos do código onde possível (ex: versão do pyproject.toml) |
| Exemplos de Claude Desktop podem variar por OS | Documentar para macOS, Linux e Windows |
| Hardening pode quebrar testes existentes | Rodar suite completa após cada mudança em D6 |
| Release prematura com bugs conhecidos | D8 só acontece após D1–D7 completas e validadas |

---

## 9. Observações

- Esta fase **não** adiciona novas tools, resources ou funcionalidades.
- Foco exclusivo em qualidade, documentação e preparação de release.
- O planejamento foi gerado com auxílio das tools `plan_feature` e `analyze_bug` do próprio Atlas MCP.
- Após esta fase: o projeto estará na versão `v0.1.0` com documentação completa para usuários externos.
- A **Fase 6** (se necessária) poderá focar em SSE transport validado, métricas/observabilidade, ou novas tools.
