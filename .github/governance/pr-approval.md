# Regras de Aprovação de Pull Requests — Atlas MCP

**Versão:** 1.0  
**Status:** APROVADO  
**Data:** 2026-02-19

---

## 1. Princípio

Toda alteração de código entra no repositório **exclusivamente** via Pull Request. Commits diretos nas branches protegidas (`main`, `develop`) são proibidos.

---

## 2. Modo de Aprovação

O projeto adota **self-merge com checklist**, ou seja, o próprio autor do PR pode aprová-lo e realizar o merge, desde que todos os critérios sejam atendidos.

---

## 3. Checklists por Nível de Destino

### 3.1 PR para `phase/P#` (tarefa → fase)

Antes de mergear uma branch de tarefa na branch de fase:

- [ ] O CI pipeline passou em todos os checks
- [ ] Código implementa **apenas** o escopo da tarefa (`D#`)
- [ ] Nenhum arquivo fora do escopo foi alterado
- [ ] Testes relevantes foram adicionados/atualizados
- [ ] `ruff check .` passa sem erros
- [ ] `ruff format --check .` passa sem erros
- [ ] `mypy src/` passa sem erros
- [ ] `pytest` passa sem falhas
- [ ] Commits seguem Conventional Commits com escopo `(P#-D#)`
- [ ] Descrição do PR está preenchida conforme template

### 3.2 PR para `develop` (fase → develop)

Antes de mergear uma branch de fase na `develop`:

- [ ] **Todas** as tarefas da fase (D1 a DN) foram mergeadas na `phase/P#`
- [ ] Não existem branches de tarefa abertas com trabalho pendente
- [ ] O CI pipeline passa na `phase/P#`
- [ ] Todos os critérios de validação da fase foram atendidos
- [ ] Nenhum conflito de merge pendente
- [ ] CHANGELOG.md foi atualizado (se aplicável)

### 3.3 PR para `main` (develop → main)

Antes de mergear `develop` na `main`:

- [ ] Todos os checks dos níveis anteriores foram cumpridos
- [ ] O CI pipeline passa na `develop`
- [ ] A `develop` está estável e testada
- [ ] Tags de release estão preparadas (`phase-N-complete` + `vX.Y.Z`)
- [ ] CHANGELOG.md está atualizado com as mudanças da fase
- [ ] Nenhuma feature incompleta na `develop`

---

## 4. Merge de Hotfix

Para PRs de hotfix na `main`:

- [ ] Hotfix corrige **apenas** o problema identificado
- [ ] Testes de regressão foram adicionados
- [ ] CI passa em todos os checks
- [ ] Após merge na `main`, merge realizado na `develop`
- [ ] Se há `phase/P#` ativa, merge realizado nela também

---

## 5. Regras Gerais

| Regra | Descrição |
|-------|-----------|
| **Self-merge** | Permitido em todos os níveis |
| **CI obrigatório** | Nenhum merge sem CI passando |
| **Template obrigatório** | PRs devem usar o template definido |
| **Escopo restrito** | Cada PR deve conter apenas alterações da tarefa correspondente |
| **Squash merge** | Recomendado para branches de tarefa (mantém histórico limpo) |
| **Merge commit** | Usado para merges de fase → develop e develop → main |

---

## 6. O Que Não Fazer

- ❌ Mergear com CI falhando
- ❌ Mergear sem preencher o template de PR
- ❌ Incluir alterações de múltiplas tarefas em um único PR
- ❌ Realizar force push em branches compartilhadas
- ❌ Deletar branches após merge (mantemos para histórico)

---

Estas regras são **obrigatórias** e se aplicam a todos os Pull Requests do projeto Atlas MCP.
