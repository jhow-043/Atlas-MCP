# Convenção de Commits — Atlas MCP

**Versão:** 1.0  
**Status:** APROVADO  
**Data:** 2026-02-19

---

## 1. Padrão Adotado

Este projeto segue o padrão **[Conventional Commits](https://www.conventionalcommits.org/pt-br/)** com escopo obrigatório vinculado à fase e tarefa.

---

## 2. Formato

```
<tipo>(<escopo>): <descrição>

[corpo opcional]

[rodapé opcional]
```

### Regras:

- **Tipo:** obrigatório (ver tabela abaixo)
- **Escopo:** obrigatório, no formato `P#-D#` (fase e tarefa)
- **Descrição:** obrigatória, imperativo, sem ponto final, máximo 72 caracteres
- **Corpo:** opcional, detalhes adicionais
- **Rodapé:** opcional, referências (issues, breaking changes)

---

## 3. Tipos de Commit

| Tipo       | Quando usar                            | Exemplo                                     |
|------------|----------------------------------------|----------------------------------------------|
| `feat`     | Nova funcionalidade                    | `feat(P1-D3): implementar ResourceRegistry`  |
| `fix`      | Correção de bug                        | `fix(P2-D1): corrigir parse de JSON-RPC`     |
| `docs`     | Alteração em documentação              | `docs(P0-D4): criar README.md com badges`    |
| `chore`    | Tarefas de manutenção / setup          | `chore(P0-D3): configurar pyproject.toml`    |
| `ci`       | Alteração em CI/CD                     | `ci(P0-D7): configurar GitHub Actions`       |
| `test`     | Adição ou correção de testes           | `test(P1-D7): adicionar testes do handler`   |
| `refactor` | Refatoração sem alterar comportamento  | `refactor(P3-D5): extrair lógica de chunking`|
| `style`    | Formatação, sem mudança de lógica      | `style(P1-D2): aplicar formatação Ruff`      |
| `perf`     | Melhoria de performance                | `perf(P3-D6): otimizar busca vetorial`       |

---

## 4. Escopo

O escopo **deve** conter o identificador da fase e tarefa no formato:

```
P<número_da_fase>-D<número_da_tarefa>
```

### Exemplos válidos:

```
feat(P1-D3): implementar ResourceRegistry com resource estático
fix(P2-D1): corrigir parse de JSON-RPC na validação de id
docs(P0-D4): criar README.md com badges e quick start
chore(P0-D3): configurar pyproject.toml com dependências
ci(P0-D7): configurar GitHub Actions para CI
test(P1-D7): adicionar testes unitários do ProtocolHandler
refactor(P3-D5): extrair lógica de chunking para módulo dedicado
```

### Exceções:

Para commits de hotfix que não pertencem a uma fase:

```
fix(hotfix): corrigir falha crítica no CI pipeline
```

---

## 5. Descrição

- Usar **imperativo** (ex.: "adicionar", "corrigir", "remover" — não "adicionado", "corrigido")
- Primeira letra **minúscula**
- **Sem ponto final**
- Máximo **72 caracteres** na primeira linha

---

## 6. Corpo (Opcional)

Separado da descrição por uma linha em branco. Use para:

- Explicar **o que** e **por que** (não o como)
- Contexto adicional sobre a mudança
- Referências a issues ou ADRs

```
feat(P1-D3): implementar ResourceRegistry com resource estático

Implementa o registry de MCP Resources com suporte ao resource
context://core/stack que retorna dados mock da stack tecnológica.

O registry usa um dicionário interno para mapear URIs a handlers,
permitindo extensão futura com resources dinâmicos.

Refs: ADR-001
```

---

## 7. Breaking Changes

Indicar com `!` após o tipo ou com rodapé `BREAKING CHANGE:`:

```
feat(P4-D2)!: alterar formato de resposta do search_context

BREAKING CHANGE: O campo `results` agora retorna objetos com
`similarity` em vez de `score`. Clientes devem ser atualizados.
```

---

## 8. Commits Não Permitidos

- Commits sem tipo: ~~`corrigir bug no handler`~~
- Commits sem escopo: ~~`feat: adicionar resource`~~
- Commits fora do padrão: ~~`WIP`, `fix stuff`, `update`~~
- Commits com múltiplos escopos: ~~`feat(P1-D1,P1-D2): ...`~~

---

## 9. Relação Tipo ↔ Branch

| Tipo de Branch | Tipos de commit esperados      |
|----------------|--------------------------------|
| `FET/P#-D#`   | `feat`, `test`, `docs`         |
| `BUG/P#-D#`   | `fix`, `test`                  |
| `REF/P#-D#`   | `refactor`, `test`, `style`    |
| `INF/P#-D#`   | `chore`, `ci`                  |
| `DOC/P#-D#`   | `docs`                         |
| `TST/P#-D#`   | `test`                         |
| `hotfix/*`     | `fix`                          |

---

Esta convenção é **obrigatória** e deve ser seguida em todos os commits do projeto Atlas MCP.
