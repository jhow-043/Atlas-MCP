# Fase 1 — Fundação e Protocolo MCP

**Status:** APROVADO  
**Data:** 2026-02-19  
**Versão:** 2.0  
**Repositório:** `https://github.com/jhow-043/Atlas-MCP.git`

---

## 1. Objetivo da Fase

Estabelecer a base do servidor MCP com comunicação JSON-RPC 2.0 funcional, incluindo:

- Projeto Python (`atlas_mcp`) com uv, linting (Ruff) e testes (pytest) já configurados na Fase 0
- Servidor MCP funcional com transporte stdio
- Capability negotiation completo (`initialize`/`initialized`)
- Resources e Tools com implementações básicas
- Error handling conforme especificação JSON-RPC 2.0
- Documentação para execução local

Ao final desta fase, o servidor deve conectar com o **MCP Inspector** e responder a todas as operações básicas do protocolo.

---

## 2. Tarefas (8/8)

| # | Tipo | Branch | Tarefa | Output |
|---|------|--------|--------|--------|
| D1 | `INF` | `INF/P1-D1` | Validar setup da Fase 0: `uv sync`, `ruff check .`, `ruff format --check .`, `mypy src/`, `pytest` passam. Ajustar se necessário. | Todos os comandos de validação passam sem erros |
| D2 | `FET` | `FET/P1-D2` | Implementar `ProtocolHandler` — camada de parse/serialize JSON-RPC 2.0 usando o SDK MCP. Configurar `Server` com transporte stdio. | Servidor inicializa e aceita conexão via stdio |
| D3 | `FET` | `FET/P1-D3` | Implementar capability negotiation — configurar `initialize`/`initialized` com declaração de capabilities: `resources`, `tools` | Handshake MCP funcional via Inspector |
| D4 | `FET` | `FET/P1-D4` | Implementar `ResourceRegistry` — registry de resources com ao menos um resource estático (`context://core/stack`) retornando dados mock da stack tecnológica | `resources/list` e `resources/read` funcionais |
| D5 | `FET` | `FET/P1-D5` | Implementar `ToolExecutor` — executor de tools com ao menos uma tool mock (`search_context`) com input schema validado | `tools/list` e `tools/call` funcionais |
| D6 | `FET` | `FET/P1-D6` | Implementar error handling — tratar erros conforme JSON-RPC 2.0 (MethodNotFound, InvalidParams, InternalError). Respostas de erro padronizadas. | Erros retornados com códigos corretos |
| D7 | `TST` | `TST/P1-D7` | Escrever testes unitários para `ProtocolHandler`, `ResourceRegistry` e `ToolExecutor` com pytest + pytest-asyncio | Suite de testes com cobertura ≥ 80% para protocolo |
| D8 | `DOC` | `DOC/P1-D8` | Atualizar README.md com instruções de instalação, build, execução e teste. Incluir pré-requisitos. | README completo e funcional |

---

## 3. Dependências

| Tarefa | Depende de |
|--------|------------|
| D2 (ProtocolHandler) | D1 (Setup validado) |
| D3 (Capability negotiation) | D2 (ProtocolHandler) |
| D4 (ResourceRegistry) | D2 (ProtocolHandler) |
| D5 (ToolExecutor) | D2 (ProtocolHandler) |
| D6 (Error handling) | D2 (ProtocolHandler) |
| D7 (Testes) | D4, D5, D6 |
| D8 (Documentação) | D1, D2, D3 |

**Grafo de dependências:**

```
[D1] Setup
 └──→ [D2] ProtocolHandler
       ├──→ [D3] Capability Negotiation
       ├──→ [D4] ResourceRegistry ──→ [D7] Testes
       ├──→ [D5] ToolExecutor ─────→ [D7] Testes
       └──→ [D6] Error Handling ───→ [D7] Testes
 └──→ [D8] Documentação (parcial, finalizada após D3)
```

---

## 4. Outputs Esperados

| Artefato | Localização |
|----------|-------------|
| ProtocolHandler | `src/atlas_mcp/protocol/handler.py` |
| ResourceRegistry | `src/atlas_mcp/resources/registry.py` |
| Resource core/stack | `src/atlas_mcp/resources/core_stack.py` |
| ToolExecutor | `src/atlas_mcp/tools/executor.py` |
| Tool search_context | `src/atlas_mcp/tools/search_context.py` |
| Server setup (atualizado) | `src/atlas_mcp/server.py` |
| Entry point (atualizado) | `src/atlas_mcp/__main__.py` |
| Testes unitários | `tests/unit/test_handler.py`, `tests/unit/test_registry.py`, `tests/unit/test_executor.py` |
| Documentação (atualizada) | `README.md` |

### Estrutura de diretórios esperada:

```
Atlas-MCP/
├── src/
│   └── atlas_mcp/
│       ├── __init__.py               # Package init
│       ├── __main__.py               # Entry point (python -m atlas_mcp)
│       ├── server.py                 # MCP Server setup
│       ├── protocol/
│       │   ├── __init__.py
│       │   └── handler.py            # ProtocolHandler
│       ├── resources/
│       │   ├── __init__.py
│       │   ├── registry.py           # ResourceRegistry
│       │   └── core_stack.py         # Resource: context://core/stack
│       └── tools/
│           ├── __init__.py
│           ├── executor.py           # ToolExecutor
│           └── search_context.py     # Tool: search_context (mock)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Fixtures compartilhadas
│   └── unit/
│       ├── __init__.py
│       ├── test_init.py              # Smoke tests (Fase 0)
│       ├── test_handler.py           # Testes do ProtocolHandler
│       ├── test_registry.py          # Testes do ResourceRegistry
│       └── test_executor.py          # Testes do ToolExecutor
├── pyproject.toml
├── ruff.toml
├── uv.lock
└── README.md
```

---

## 5. Critérios de Validação

| # | Critério | Método de Verificação |
|---|----------|----------------------|
| 1 | Projeto executa sem erros com `uv run python -m atlas_mcp` | Execução direta |
| 2 | Servidor inicializa via stdio sem crash | Execução manual |
| 3 | MCP Inspector conecta e lista capabilities | Teste com Inspector |
| 4 | `resources/list` retorna resource `context://core/stack` | Teste automatizado + Inspector |
| 5 | `resources/read` retorna conteúdo JSON válido | Teste automatizado + Inspector |
| 6 | `tools/list` retorna tool `search_context` com schema válido | Teste automatizado + Inspector |
| 7 | `tools/call` com input válido retorna resultado mock | Teste automatizado |
| 8 | `tools/call` com input inválido retorna erro JSON-RPC correto | Teste automatizado |
| 9 | Todos os testes passam com `uv run pytest` | Execução da suite |
| 10 | `uv run mypy src/` passa sem erros | Execução direta |
| 11 | `uv run ruff check .` e `uv run ruff format --check .` passam | Execução direta |
| 12 | README contém instruções suficientes para execução independente | Revisão manual |

---

## 6. Stack Tecnológica da Fase

| Componente | Tecnologia | Versão |
|------------|------------|--------|
| Runtime | Python | ≥ 3.12 |
| Gerenciador de pacotes | uv | latest |
| MCP SDK | `mcp` (SDK oficial Python) | latest |
| Testes | pytest + pytest-asyncio | latest |
| Lint + Formatação | Ruff | latest |
| Type checking | mypy (obrigatório, strict mode) | latest |

---

## 7. Riscos da Fase

| Risco | Mitigação |
|-------|-----------|
| Incompatibilidade de versão do SDK MCP Python | Fixar versão no `pyproject.toml`. Testar com Inspector antes de avançar. |
| Complexidade do JSON-RPC 2.0 manual | Usar SDK oficial Python (`mcp`) que abstrai a camada de protocolo. |
| Compatibilidade de versão Python | Exigir Python ≥ 3.12. Usar `uv` para gerenciamento de ambiente isolado. |
| Type stubs incompletos do SDK `mcp` com mypy strict | Configurar overrides de mypy no `pyproject.toml` para o pacote `mcp` se necessário (`disallow_untyped_calls = false` por módulo). Avaliar uso de `type: ignore` pontual com justificativa. |

---

## 8. Observações

- Esta fase **não** inclui banco de dados, vetorização ou governança funcional. Esses são escopo das Fases 2, 3 e 4.
- O resource `context://core/stack` e a tool `search_context` usam **dados mock** nesta fase. Serão conectados a dados reais na Fase 2.
- O servidor utiliza **transporte stdio** por padrão, conforme recomendado pela spec MCP para desenvolvimento local.

---

> **Próximo passo:** Criar branch `phase/P1` a partir da `develop` e iniciar execução pela tarefa D1.
