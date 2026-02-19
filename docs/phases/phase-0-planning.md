# Fase 0 — Fundação do Repositório Atlas MCP

**Status:** APROVADO  
**Data:** 2026-02-19  
**Versão:** 2.0  
**Repositório:** `https://github.com/jhow-043/Atlas-MCP.git`

---

## 1. Objetivo da Fase

Estruturar o repositório `Atlas-MCP` no GitHub de forma profissional, estabelecendo:

- Repositório conectado ao remote com `.gitignore` funcional
- Estrutura de diretórios completa para projeto Python MCP
- Configuração do projeto Python com `uv`, Ruff e pytest
- Documentação base (README, CONTRIBUTING, LICENSE, CHANGELOG, CODE_OF_CONDUCT)
- Templates padronizados de Issues e Pull Requests
- Documentos de governança em `.github/governance/`
- CI pipeline funcional via GitHub Actions
- Branches `main` e `develop` criadas com política de branching ativa

**Exceção de Fase 0:** Commits iniciais na `main` são permitidos até a criação da `develop` (D1–D3). Proteção da `main` ativada após conclusão desta fase.

---

## 2. Tarefas (8/8)

| # | Tipo | Branch | Tarefa | Output |
|---|------|--------|--------|--------|
| D1 | `INF` | `main` (bootstrap) | Inicializar repositório, `.gitignore`, `.python-version`, conectar remote | Repo conectado ao GitHub |
| D2 | `INF` | `main` (bootstrap) | Criar estrutura de diretórios com `__init__.py` | Árvore completa do projeto |
| D3 | `INF` | `main` (bootstrap) | `pyproject.toml`, `ruff.toml`, `uv sync` — **criar `develop` e `phase/P0` após** | Projeto Python configurado |
| D4 | `DOC` | `DOC/P0-D4` | README, CONTRIBUTING, CODE_OF_CONDUCT, LICENSE, CHANGELOG | Documentação base completa |
| D5 | `DOC` | `DOC/P0-D5` | Governança em `.github/governance/` (branching, commits, dev governance, PR rules) | Políticas formalizadas |
| D6 | `INF` | `INF/P0-D6` | Templates de issues (bug, feature, task) e PR | Templates visíveis no GitHub |
| D7 | `INF` | `INF/P0-D7` | GitHub Actions CI (`ci.yml`) | Pipeline CI funcional |
| D8 | `DOC` | `DOC/P0-D8` | Mover `context.md`, criar ADR template + ADR-001 + ADR-002, organizar docs | Documentação organizada |

---

## 3. Dependências

```
[D1] → [D2] → [D3] → criar develop + phase/P0
                        ├── [D4] ──→ [D8]
                        ├── [D5] ──→ [D8]
                        ├── [D6]
                        └── [D7]
```

---

## 4. Critérios de Validação

1. `git clone` funciona e estrutura completa
2. `uv sync` instala dependências
3. `uv run ruff check .` / `ruff format --check .` passam
4. `uv run pytest` executa
5. GitHub Actions CI roda no push
6. Templates de issue/PR aparecem no GitHub
7. Branch `develop` existe
8. Governança em `.github/governance/`
9. ADRs em `docs/adr/`
10. Tags `phase-0-complete` + `v0.0.1`
