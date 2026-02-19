# Política de Branching e Governança por Fase — Atlas MCP

**Versão:** 1.0  
**Status:** APROVADO  
**Data:** 2026-02-19

---

## 1. Objetivo

Estabelecer um modelo rigoroso de organização de desenvolvimento baseado em:

- Planejamento por fases (máximo 8 tarefas por fase)
- Uma branch por tarefa
- Isolamento completo da branch principal
- Rastreabilidade obrigatória entre tarefa, branch, commit e merge

A branch `main` deve permanecer **sempre estável e pronta para produção**.

---

## 2. Estrutura de Branches

### 2.1 Branch Principal — `main`

- Representa código estável e validado.
- **Não** é permitido commit direto.
- Merge somente via Pull Request aprovado (self-merge permitido com CI passando).
- Deve estar sempre em estado deployável.
- Recebe merges exclusivamente da `develop`.

### 2.2 Branch de Desenvolvimento — `develop`

- Criada a partir da `main`.
- Representa o estado consolidado de desenvolvimento.
- Recebe merges das branches de fase (`phase/P#`).
- Serve como camada de staging antes da `main`.
- Periodicamente mergeada na `main` (release).

### 2.3 Branch de Fase — `phase/P#`

Formato:

```
phase/P<numero>
```

Exemplos: `phase/P0`, `phase/P1`, `phase/P2`

Regras:

- Criada a partir da `develop`.
- Representa o estado consolidado da fase.
- Recebe merges das branches de tarefa da fase.
- **Não** deve receber commits diretos.
- Ao concluir todas as tarefas, merge na `develop`.

### 2.4 Branch de Tarefa — `TIPO/P#-D#`

Formato obrigatório:

```
<TIPO>/P<fase>-D<tarefa>
```

Exemplos: `FET/P1-D1`, `BUG/P2-D3`, `INF/P0-D1`, `DOC/P0-D4`

Regras:

- Criada a partir de `phase/P#`.
- Contém apenas **uma** tarefa.
- Não pode acumular múltiplos escopos.
- Não pode conter código não relacionado à tarefa.
- Merge via PR na `phase/P#` correspondente.

### 2.5 Branch de Hotfix — `hotfix/<identificador>`

Formato:

```
hotfix/<identificador>
```

Exemplo: `hotfix/fix-ci-pipeline`

Regras:

- Criada a partir da `main`.
- Corrige bug crítico em produção.
- Após correção:
  1. Merge na `main`.
  2. Merge na `develop`.
  3. Se existir `phase/P#` ativa, merge nela também.

---

## 3. Tipos de Branch de Tarefa

| Tipo  | Uso                                    | Commit prefix |
|-------|----------------------------------------|---------------|
| `FET` | Nova funcionalidade                    | `feat`        |
| `BUG` | Correção de defeito                    | `fix`         |
| `REF` | Refatoração                            | `refactor`    |
| `INF` | Infraestrutura / setup / configuração  | `chore` / `ci`|
| `DOC` | Documentação                           | `docs`        |
| `TST` | Testes isolados                        | `test`        |

---

## 4. Fluxo de Desenvolvimento

```
main
 └── develop
      └── phase/P#
           ├── TIPO/P#-D1
           ├── TIPO/P#-D2
           ├── ...
           └── TIPO/P#-D8 (máximo)
```

### Passo a passo:

1. Criar `phase/P#` a partir da `develop`.
2. Definir tarefas da fase (máximo 8, identificadas de D1 a D8).
3. Criar branch da tarefa a partir de `phase/P#`.
4. Implementar **apenas** o escopo da tarefa.
5. Abrir Pull Request para `phase/P#`.
6. Validar: CI passando + checklist de validação.
7. Realizar merge (self-merge permitido).
8. Repetir para todas as tarefas da fase.
9. Ao concluir todas as tarefas, abrir PR de `phase/P#` → `develop`.
10. Após validação na `develop`, abrir PR de `develop` → `main`.
11. Criar tags de release na `main`.

---

## 5. Limite de Tarefas

- Cada fase pode conter **no máximo 8 tarefas**.
- Identificação: `D1` a `D8`.
- Não utilizar `D0`.
- A branch de fase (`phase/P#`) **não** é uma tarefa.

---

## 6. Tags e Versionamento

Ao finalizar uma fase e mergear na `main`, criar **duas tags**:

### Tag descritiva:

```
phase-<N>-complete
```

### Tag SemVer:

```
v<MAJOR>.<MINOR>.<PATCH>
```

### Progressão planejada:

| Fase | Tag descritiva       | Tag SemVer |
|------|---------------------|------------|
| P0   | `phase-0-complete`  | `v0.0.1`   |
| P1   | `phase-1-complete`  | `v0.1.0`   |
| P2   | `phase-2-complete`  | `v0.2.0`   |
| P3   | `phase-3-complete`  | `v0.3.0`   |
| P4   | `phase-4-complete`  | `v0.4.0`   |
| P5   | `phase-5-complete`  | `v1.0.0`   |

---

## 7. Retenção de Branches

- Branches de tarefa (`TIPO/P#-D#`): **mantidas** após merge para histórico.
- Branches de fase (`phase/P#`): **mantidas** após merge para histórico.
- Branches de hotfix (`hotfix/*`): **mantidas** após merge para histórico.

---

## 8. Aprovação de Pull Requests

| Destino      | Requisito de aprovação                    |
|-------------|-------------------------------------------|
| `phase/P#`  | CI passando + self-review via checklist    |
| `develop`   | CI passando + todas as tarefas mergeadas   |
| `main`      | CI passando + validação na `develop`       |

Self-merge é permitido em todos os níveis, desde que o CI esteja passando e os critérios de validação da fase sejam atendidos.

---

## 9. Regras de Governança

1. É **proibido** criar branch fora do padrão definido.
2. É **proibido** alterar código fora do escopo da tarefa.
3. É **proibido** fazer commit direto na `main`.
4. É **proibido** fazer commit direto na `develop` (exceto merge de fase/hotfix).
5. Toda alteração deve ser rastreável por fase e tarefa.
6. A `main` deve permanecer estável em todos os momentos.
7. Commits devem seguir Conventional Commits com escopo `(P#-D#)`.

---

## 10. Encerramento de Fase

Uma fase é considerada concluída quando:

- [ ] Todas as tarefas (D1 a DN) foram mergeadas na `phase/P#`.
- [ ] Não existem branches abertas da fase com trabalho pendente.
- [ ] A `phase/P#` foi mergeada na `develop`.
- [ ] A `develop` foi mergeada na `main`.
- [ ] Tags foram criadas (`phase-N-complete` + `vX.Y.Z`).
- [ ] A `main` encontra-se estável após validação.
- [ ] CI passa em todos os checks na `main`.

---

## 11. Exceção — Fase 0 (Fundação)

A Fase 0 é a fase de **criação do próprio repositório e estrutura**. Como a política de branching ainda não existe no momento da sua execução:

- A Fase 0 **pode** ter commits iniciais diretamente na `main` para bootstrap.
- A partir da criação da `develop`, o fluxo completo deve ser seguido.
- A proteção da `main` é ativada **após** a conclusão da Fase 0.

---

## 12. Diagrama Visual do Fluxo

```
main ─────────────────────────────────────────── ● tag: v0.1.0
  │                                              ▲
  └─→ develop ──────────────────────────────── merge
        │                                        ▲
        └─→ phase/P1 ────────────────────────── merge
              │         │         │              ▲
              ├─→ FET/P1-D1 ── merge ─┐         │
              ├─→ FET/P1-D2 ── merge ─┤         │
              ├─→ BUG/P1-D3 ── merge ─┤         │
              └─→ INF/P1-D4 ── merge ─┘─────────┘

  hotfix/fix-critical ─→ merge main + develop + phase ativa
```

---

Este modelo é **obrigatório** e deve ser seguido integralmente em todos os ciclos de desenvolvimento do projeto Atlas MCP.
