# Guia de Contribuição — Atlas MCP

Obrigado pelo interesse em contribuir com o Atlas MCP! Este documento descreve como configurar o ambiente, o fluxo de trabalho e as convenções que seguimos.

---

## Pré-requisitos

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) (gerenciador de pacotes)
- Git

## Setup Local

```bash
# Clone o repositório
git clone https://github.com/jhow-043/Atlas-MCP.git
cd Atlas-MCP

# Instale todas as dependências (incluindo dev)
uv sync --all-extras

# Verifique se está tudo funcionando
uv run pytest
uv run ruff check .
uv run mypy src/
```

---

## Política de Branching

Seguimos uma política rigorosa de branching documentada em [`.github/governance/branching-policy.md`](.github/governance/branching-policy.md).

### Resumo

```
main ← develop ← phase/P# ← TIPO/P#-D#
```

- **`main`** — Código estável, pronto para produção. Sem commits diretos.
- **`develop`** — Staging. Recebe merges de fases concluídas.
- **`phase/P#`** — Branch de fase. Recebe merges de tarefas.
- **`TIPO/P#-D#`** — Branch de tarefa individual.

### Tipos de Branch

| Tipo  | Uso                                    |
|-------|----------------------------------------|
| `FET` | Nova funcionalidade                    |
| `BUG` | Correção de defeito                    |
| `REF` | Refatoração                            |
| `INF` | Infraestrutura / setup / configuração  |
| `DOC` | Documentação                           |
| `TST` | Testes isolados                        |

### Exemplos

```
FET/P1-D3    # Feature, Fase 1, Tarefa 3
BUG/P2-D1    # Bug fix, Fase 2, Tarefa 1
INF/P0-D7    # Infra, Fase 0, Tarefa 7
```

---

## Convenção de Commits

Seguimos **Conventional Commits** com escopo obrigatório `(P#-D#)`:

```
<tipo>(<escopo>): <descrição>
```

### Exemplos

```
feat(P1-D3): implementar ResourceRegistry com resource estático
fix(P2-D1): corrigir parse de JSON-RPC na validação de id
docs(P0-D4): criar README.md com badges e quick start
chore(P0-D3): configurar pyproject.toml com dependências
ci(P0-D7): configurar GitHub Actions para CI
test(P1-D6): adicionar testes unitários do ProtocolHandler
refactor(P3-D5): extrair lógica de chunking para módulo dedicado
```

### Tipos de Commit

| Tipo       | Quando usar                            |
|------------|----------------------------------------|
| `feat`     | Nova funcionalidade                    |
| `fix`      | Correção de bug                        |
| `docs`     | Alteração em documentação              |
| `chore`    | Tarefas de manutenção / setup          |
| `ci`       | Alteração em CI/CD                     |
| `test`     | Adição ou correção de testes           |
| `refactor` | Refatoração sem alterar comportamento  |
| `style`    | Formatação, sem mudança de lógica      |
| `perf`     | Melhoria de performance                |

Documentação completa: [`.github/governance/commit-convention.md`](.github/governance/commit-convention.md)

---

## Processo de Pull Request

1. Crie sua branch a partir de `phase/P#` seguindo a convenção de nomes.
2. Implemente **apenas** o escopo da tarefa atribuída.
3. Garanta que todos os checks passam:
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run mypy src/`
   - `uv run pytest`
4. Abra um Pull Request para `phase/P#`.
5. Preencha o template de PR.
6. Após CI passar, realize o merge (self-merge permitido).

---

## Governança

O desenvolvimento segue fases com no máximo **8 tarefas** cada, obedecendo o ciclo:

> **Planejamento → Revisão → Aprovação → Execução**

Detalhes completos: [`.github/governance/development-governance.md`](.github/governance/development-governance.md)
