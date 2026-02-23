# P1-D6 — Error Handling conforme JSON-RPC 2.0

## Objetivo

Implementar tratamento de erros padronizado no Atlas MCP, garantindo que erros
retornados ao cliente seguem a especificação JSON-RPC 2.0 com códigos e 
mensagens corretos.

## Análise do SDK

O SDK MCP (`mcp` v1.26.0) já trata erros automaticamente em várias camadas:

| Cenário | Tratamento do SDK | Resultado |
|---------|-------------------|-----------|
| Método inexistente | `Server._handle_request()` → `ErrorData(code=METHOD_NOT_FOUND)` | JSON-RPC error response |
| Request inválido | `BaseSession._receive_loop()` → `ErrorData(code=INVALID_PARAMS)` | JSON-RPC error response |
| `McpError` em handler | `Server._handle_request()` → `err.error` | JSON-RPC error com code custom |
| Exception genérica em handler | `Server._handle_request()` → `ErrorData(code=0)` | JSON-RPC error response |
| Tool não encontrada | `ToolManager.call_tool()` → `ToolError` → catch → `CallToolResult(isError=True)` | Tool result com isError |
| Validação de input de tool | `jsonschema.ValidationError` → `_make_error_result()` | `CallToolResult(isError=True)` |
| Exception em tool | catch genérico → `_make_error_result(str(e))` | `CallToolResult(isError=True)` |

### Classes disponíveis no SDK

- `McpError(ErrorData)` — exceção que vira JSON-RPC error response
- `ErrorData(code, message, data)` — payload do erro
- `ToolError` — exceção de tool → vira `CallToolResult(isError=True)`
- Constantes: `PARSE_ERROR=-32700`, `INVALID_REQUEST=-32600`, `METHOD_NOT_FOUND=-32601`, `INVALID_PARAMS=-32602`, `INTERNAL_ERROR=-32603`

## Escopo

| Item | Descrição |
|------|-----------|
| `errors.py` | Módulo de exceções customizadas do Atlas MCP com helpers |
| `search_context.py` | Adicionar validação de parâmetros com mensagens de erro claras |
| Testes | Validar erros via protocolo: tool inexistente, parâmetros inválidos, exceção interna, erros de validação |

## Arquivos

### Novos
- `src/atlas_mcp/protocol/errors.py` — exceções + helpers
- `tests/unit/test_errors.py` — testes de error handling

### Modificados
- `src/atlas_mcp/tools/search_context.py` — validação de parâmetros

## Design

### `errors.py`

```python
class AtlasMCPError(Exception):
    """Base exception for Atlas MCP errors."""

class InvalidParameterError(AtlasMCPError):
    """Raised when a tool parameter is invalid."""

class ContextNotFoundError(AtlasMCPError):
    """Raised when a requested context is not found."""

def create_error_data(code: int, message: str, data: Any = None) -> ErrorData:
    """Create an ErrorData instance with standard format."""

def create_tool_error_response(error: Exception) -> str:
    """Format an exception as a JSON error response for tools."""
```

### `search_context.py` (validação adicionada)

```python
if not query or not query.strip():
    raise ToolError("Parameter 'query' must be a non-empty string")
if limit < 1:
    raise ToolError("Parameter 'limit' must be >= 1")
if not (0.0 <= similarity_threshold <= 1.0):
    raise ToolError("Parameter 'similarity_threshold' must be between 0.0 and 1.0")
```

### Testes

- Tool inexistente → `CallToolResult(isError=True)`
- Query vazia → `CallToolResult(isError=True)` com mensagem
- Limit inválido → `CallToolResult(isError=True)` com mensagem
- Threshold fora de range → `CallToolResult(isError=True)` com mensagem
- Tipo de parâmetro errado → `CallToolResult(isError=True)`
- Resource inexistente → `McpError`
- Erros têm formato padronizado (JSON com `error_code`, `message`, `details`)

## Critérios de Aceite

- [ ] Módulo de erros criado e exportado
- [ ] Validação de parâmetros no `search_context`
- [ ] Erros retornados com `isError=True` e mensagens claras
- [ ] Testes cobrem cenários de erro listados
- [ ] Testes ≥ 80% cobertura
- [ ] Validação completa: ruff, mypy, pytest

## Branch

`FET/P1-D6` a partir de `phase/P1` (com D5 merged)
