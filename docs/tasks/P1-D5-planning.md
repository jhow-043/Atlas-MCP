# P1-D5 — ToolExecutor com Tool `search_context` (Mock)

## Objetivo

Criar a infraestrutura de registro de tools no Atlas MCP, seguindo o mesmo
padrão do `ResourceRegistry`, e implementar o primeiro tool `search_context`
com dados mock.

## Escopo

| Item | Descrição |
|------|-----------|
| `search_context` tool | Tool com parâmetros `query`, `filters`, `limit`, `similarity_threshold`. Retorna JSON mock. |
| `ToolExecutor` | Classe estática com `register(server)` — ponto central de registro de todos os tools. |
| `handler.py` | Adicionar `ToolExecutor.register(self._server)` no `_configure_capabilities()`. |
| Testes | Cobertura completa: registro, listagem, chamada, validação de schema. |

## Arquivos

### Novos
- `src/atlas_mcp/tools/search_context.py`
- `src/atlas_mcp/tools/executor.py`
- `tests/unit/test_executor.py`

### Modificados
- `src/atlas_mcp/tools/__init__.py` — re-exportar `ToolExecutor`
- `src/atlas_mcp/protocol/handler.py` — adicionar `ToolExecutor.register()`

## Design

### `search_context.py`

```python
register_search_context(server: FastMCP) -> None:
    @server.tool()
    async def search_context(
        query: str,
        filters: dict[str, str] | None = None,
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> str:
        # retorna JSON mock
```

### `executor.py`

```python
class ToolExecutor:
    @staticmethod
    def register(server: FastMCP) -> None:
        register_search_context(server)
```

### `handler.py` (diff)

```python
  from atlas_mcp.resources import ResourceRegistry
+ from atlas_mcp.tools import ToolExecutor

  def _configure_capabilities(self) -> None:
      ResourceRegistry.register(self._server)
+     ToolExecutor.register(self._server)
```

## Critérios de Aceite

- [ ] `search_context` registrado e acessível via handshake
- [ ] Capability `tools` aparece na negociação
- [ ] Chamada retorna JSON mock válido
- [ ] Parâmetros opcionais funcionam
- [ ] Testes ≥ 80% de cobertura no módulo
- [ ] Validação completa: ruff, mypy, pytest

## Branch

`FET/P1-D5` a partir de `phase/P1` (com D4 merged)
