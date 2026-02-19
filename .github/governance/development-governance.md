# Governança de Desenvolvimento — Atlas MCP

**Versão:** 1.0  
**Status:** APROVADO  
**Data:** 2026-02-19

---

## 1. Princípio Fundamental

Todo desenvolvimento deve seguir obrigatoriamente o ciclo:

```
Planejamento → Revisão → Aprovação → Execução
```

**Nenhum artefato produzido sem planejamento prévio é válido.**

---

## 2. Desenvolvimento Baseado em Fases

Todo desenvolvimento é dividido em **fases** claramente definidas.

### Regras por fase:

- Cada fase contém **no máximo 8 tarefas**.
- Tarefas devem ser **atômicas, objetivas e bem escopladas**.
- Itens vagos ou excessivamente amplos não são permitidos.
- Se uma fase exceder 8 tarefas, deve ser **dividida em múltiplas fases**.

---

## 3. Planejamento Obrigatório

Antes de iniciar qualquer fase, um **documento formal de planejamento** deve ser criado.

### O documento deve conter:

| Seção | Descrição |
|-------|-----------|
| **Objetivo da fase** | Descrição clara do que a fase entrega |
| **Lista de tarefas** | Máximo 8, com ID (`D1` a `D8`), tipo de branch, descrição e output esperado |
| **Dependências** | Relações entre tarefas e com fases anteriores |
| **Outputs esperados** | Lista de artefatos produzidos |
| **Critérios de validação** | Como verificar que a fase está concluída |
| **Riscos** | Riscos identificados e mitigações |

### Localização:

```
docs/phases/phase-<N>-planning.md
```

### Regra inquebrantável:

> Se o planejamento não existe, o desenvolvimento **não pode** prosseguir.

Nenhuma implementação, geração de código, definição de arquitetura ou especificação técnica deve ser produzida antes da fase de planejamento estar **concluída e validada**.

---

## 4. Disciplina de Execução

- Toda implementação deve seguir **estritamente** o planejamento aprovado.
- Nada pode ser criado **fora do escopo** do plano da fase atual.
- Cada tarefa deve ser implementada em sua **branch dedicada** (`TIPO/P#-D#`).

### Se novos requisitos surgirem durante a execução:

1. Uma **nova fase de planejamento** deve ser criada.
2. O escopo deve ser **atualizado formalmente**.
3. **Nenhuma implementação ad-hoc** é permitida.

---

## 5. Ciclo de Governança

```
┌─────────────┐
│ PLANEJAMENTO│ ← Documento formal de fase
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   REVISÃO   │ ← Validação de coerência, escopo e viabilidade
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  APROVAÇÃO  │ ← Aceite formal do plano
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  EXECUÇÃO   │ ← Implementação dentro do escopo aprovado
└─────────────┘
```

---

## 6. Rastreabilidade

Toda alteração deve ser rastreável através da cadeia:

```
Fase (P#) → Tarefa (D#) → Branch (TIPO/P#-D#) → Commits → Pull Request → Merge
```

Isso garante:

- **Auditoria completa** do histórico de mudanças
- **Responsabilização** por cada decisão e implementação
- **Reversibilidade** controlada em caso de problemas

---

## 7. Artefatos de Governança

| Artefato | Localização | Descrição |
|----------|-------------|-----------|
| Planejamento de fase | `docs/phases/phase-<N>-planning.md` | Documento formal da fase |
| ADRs | `docs/adr/ADR-<NNN>-<titulo>.md` | Decisões arquiteturais |
| Política de branching | `.github/governance/branching-policy.md` | Regras de branches |
| Convenção de commits | `.github/governance/commit-convention.md` | Padrão de commits |
| Regras de PR | `.github/governance/pr-approval.md` | Processo de aprovação |
| Changelog | `CHANGELOG.md` | Registro de mudanças |

---

## 8. Violações

As seguintes ações constituem violações da governança:

1. Implementar código sem planejamento aprovado
2. Criar tarefas fora do escopo da fase
3. Exceder o limite de 8 tarefas por fase
4. Fazer merge sem validação do CI
5. Realizar commits fora da convenção estabelecida
6. Criar branches fora do padrão definido
7. Alterar código fora do escopo da tarefa atribuída

**Artefatos produzidos em violação destas regras são considerados inválidos.**

---

## 9. Exceções

Exceções às regras de governança são permitidas **apenas** nos seguintes casos:

- **Fase 0 (Bootstrap):** Commits iniciais na `main` antes da criação da `develop`.
- **Hotfix:** Correções críticas em produção seguem fluxo simplificado (ver política de branching).

Todas as exceções devem ser **documentadas** no planejamento da fase correspondente.

---

Estas regras são **não negociáveis** e devem ser aplicadas durante todo o ciclo de vida do projeto Atlas MCP.
