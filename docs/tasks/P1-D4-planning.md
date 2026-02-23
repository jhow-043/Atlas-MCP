# P1-D4 — ResourceRegistry

**Status:** APROVADO  
**Tipo:** `FET`  
**Branch:** `FET/P1-D4`  
**Depende de:** D2 (ProtocolHandler), D3 (Capability Negotiation)  
**Data:** 2026-02-22

---

## Objetivo

Implementar `ResourceRegistry` — registry de resources com ao menos um resource estático (`context://core/stack`) retornando dados mock da stack tecnológica.

**Output esperado:** `resources/list` e `resources/read` funcionais.

---

## Contexto Técnico

O FastMCP (SDK `mcp` v1.26.0) oferece o decorator `@server.resource(uri, ...)` para registrar resources. Internamente, o `ResourceManager` armazena `FunctionResource` que o SDK expõe automaticamente via `resources/list` e `resources/read`.

A tarefa D3 criou o hook `_configure_capabilities()` no `ProtocolHandler` como ponto de extensão. D4 vai:
1. Criar a classe `ResourceRegistry` que encapsula o registro de resources no servidor.
2. Criar o resource `context://core/stack` com dados mock da stack tecnológica.
3. Integrar o `ResourceRegistry` ao `ProtocolHandler._configure_capabilities()`.

---

## Arquitetura

```
ProtocolHandler.__init__()
  └── _configure_capabilities()
        └── ResourceRegistry.register(server)
              └── register_core_stack(server)   ← context://core/stack
```

### Dados mock do `context://core/stack`

JSON com a stack tecnológica conforme definida no projeto:

```json
{
  "project": "Atlas MCP",
  "language": {"name": "Python", "version": ">=3.12"},
  "runtime": "Asyncio",
  "sdk": {"name": "mcp", "description": "SDK oficial Python do Model Context Protocol"},
  "package_manager": "uv",
  "database": {"name": "PostgreSQL", "version": "16", "extensions": ["pgvector"]},
  "testing": ["pytest", "pytest-asyncio", "pytest-cov"],
  "linting": "Ruff",
  "type_checking": {"tool": "mypy", "mode": "strict"},
  "ci": "GitHub Actions"
}
```

---

## Implementação

### 1. Criar `src/atlas_mcp/resources/core_stack.py`

- Função `register_core_stack(server: FastMCP) -> None` que registra o resource `context://core/stack` via `@server.resource(...)`.
- URI: `context://core/stack`
- Nome: `core_stack`
- Descrição: `"Core technology stack for the Atlas MCP project"`
- MIME type: `application/json`
- Retorna string JSON com dados mock da stack.

### 2. Criar `src/atlas_mcp/resources/registry.py`

- Classe `ResourceRegistry` com método estático `register(server: FastMCP) -> None`.
- Chama `register_core_stack(server)`.
- Ponto central para registrar todos os resources do servidor.
- Logging de cada resource registrado.

### 3. Atualizar `src/atlas_mcp/resources/__init__.py`

- Re-exportar `ResourceRegistry`.

### 4. Atualizar `src/atlas_mcp/protocol/handler.py`

- Em `_configure_capabilities()`, chamar `ResourceRegistry.register(self._server)`.
- Atualizar docstring para refletir que resources agora são registrados.

### 5. Criar `tests/unit/test_registry.py`

- `TestResourceRegistry`:
  - `test_should_register_resources_on_server` — valida que `register()` adiciona resources ao servidor.
  - `test_should_register_core_stack_resource` — valida que `context://core/stack` aparece na lista.

- `TestCoreStackResource`:
  - `test_should_return_valid_json` — valida que o resource retorna JSON válido.
  - `test_should_contain_project_name` — valida campo `project`.
  - `test_should_contain_language_info` — valida campo `language`.
  - `test_should_contain_database_info` — valida campo `database`.
  - `test_should_have_correct_uri` — valida a URI `context://core/stack` via `resources/list`.
  - `test_should_have_json_mime_type` — valida MIME type `application/json`.
  - `test_should_be_readable_via_protocol` — handshake in-memory + `resources/read` retorna o JSON.

---

## Decisões

| Decisão | Justificativa |
|---------|---------------|
| `ResourceRegistry` como classe com método estático `register()` | Simples, sem estado, extensível — novas resources são adicionados com chamadas adicionais dentro de `register()`. |
| Dados mock hardcoded | Conforme planning da Fase 1 — dados reais virão na Fase 2. |
| `register_core_stack()` em arquivo separado | Separação de responsabilidades — cada resource em seu arquivo. |
| MIME type `application/json` | O conteúdo é JSON estruturado. |

---

## Validação

- [ ] `resources/list` retorna `context://core/stack`
- [ ] `resources/read` retorna JSON válido com dados da stack
- [ ] `uv run ruff check .` sem erros
- [ ] `uv run ruff format --check .` sem erros
- [ ] `uv run mypy src/` sem erros
- [ ] `uv run pytest` todos passam, cobertura ≥ 80%

---

## Commit sugerido

```
feat(P1-D4): implementar ResourceRegistry com resource context://core/stack
```
