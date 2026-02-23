# P1-D3 — Capability Negotiation

**Status:** CONCLUÍDA  
**Tipo:** `FET`  
**Branch:** `FET/P1-D3`  
**Depende de:** D2 (ProtocolHandler)  
**Data:** 2026-02-22

---

## Objetivo

Implementar capability negotiation — configurar `initialize`/`initialized` com declaração de capabilities `resources` e `tools`.

**Output esperado:** Handshake MCP funcional via Inspector.

---

## Contexto Técnico

O FastMCP do SDK `mcp` (v1.26.0) lida com capability negotiation **automaticamente**: detecta handlers registrados (tools, resources, prompts) e declara as capabilities correspondentes no `InitializeResult`. O handshake `initialize`/`initialized` já funciona out-of-the-box.

A tarefa D3 foca em:
1. Criar um **hook de configuração** (`_configure_capabilities`) no `ProtocolHandler` como ponto de extensão para D4/D5.
2. Configurar a **versão do servidor** no handshake para retornar `__version__` do Atlas MCP.
3. Escrever **testes in-memory** que validam o handshake completo.

---

## Abordagem

**Hook no `ProtocolHandler`** — método `_configure_capabilities()` chamado no `__init__` após criação do servidor. No-op nesta fase; D4 e D5 adicionam registros de resources/tools.

**Testes via `ClientSession` + `anyio` in-memory** — cria servidor e cliente em memória, executa `initialize()`, valida `InitializeResult`.

---

## Alterações Realizadas

| Arquivo | Alteração |
|---------|-----------|
| `src/atlas_mcp/server.py` | `create_server()` agora define `server._mcp_server.version = __version__` |
| `src/atlas_mcp/protocol/handler.py` | Adicionado `_configure_capabilities()` + docstring com lifecycle |
| `tests/unit/test_capabilities.py` | **Novo** — 12 testes de handshake e capabilities |
| `tests/unit/test_handler.py` | Adicionado `test_should_have_configure_capabilities_method` |
| `tests/unit/test_server.py` | Adicionado `test_should_set_server_version` |

---

## Testes (12)

### TestCapabilityNegotiation (8)
- `test_should_complete_handshake_successfully`
- `test_should_return_correct_server_name`
- `test_should_return_correct_server_version`
- `test_should_return_instructions`
- `test_should_return_protocol_version`
- `test_should_declare_tools_capability`
- `test_should_declare_resources_capability`
- `test_should_expose_capabilities_via_session`

### TestCapabilityWithHandlers (2)
- `test_should_list_registered_tool`
- `test_should_list_registered_resource`

### TestConfigureCapabilities (2)
- `test_should_call_configure_capabilities_on_init`
- `test_should_have_configure_capabilities_method`

---

## Validação

- `ruff check .` ✓
- `ruff format --check .` ✓
- `mypy src/` ✓
- `pytest` — 25 testes, 100% cobertura ✓

---

## Commit

```
feat(P1-D3): implementar capability negotiation com hook de configuração
```
