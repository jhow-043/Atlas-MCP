# Fase 1 — Fundação e Protocolo MCP

**Status:** PROPOSTO  
**Data:** 2026-02-19  
**Versão:** 1.1  

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

| # | Tarefa | Descrição | Output Esperado |
|---|--------|-----------|-----------------|
| 1 | **Validar setup da Fase 0** | Verificar que `atlas_mcp` está funcional: `uv sync`, `ruff check`, `pytest` passam. Ajustar se necessário. | Ambiente validado e pronto |
| 2 | **Implementar ProtocolHandler** | Criar camada de parse/serialize JSON-RPC 2.0 usando o SDK MCP. Configurar `Server` com transporte stdio. | Servidor inicializa e aceita conexão |
| 3 | **Implementar capability negotiation** | Configurar `initialize`/`initialized` com declaração de capabilities: `resources`, `tools` | Handshake MCP funcional via Inspector |
| 4 | **Implementar ResourceRegistry** | Criar registry de resources com ao menos um resource estático (`context://core/stack`) retornando dados mock da stack tecnológica | `resources/list` e `resources/read` funcionais |
| 5 | **Implementar ToolExecutor** | Criar executor de tools com ao menos uma tool mock (`search_context`) com input schema validado | `tools/list` e `tools/call` funcionais |
| 6 | **Implementar error handling** | Tratar erros conforme JSON-RPC 2.0 (MethodNotFound, InvalidParams, InternalError). Respostas de erro padronizadas. | Erros retornados com códigos corretos |
| 7 | **Setup de testes automatizados** | Configurar pytest + pytest-asyncio. Criar testes unitários para ProtocolHandler, ResourceRegistry e ToolExecutor. | Suite de testes com cobertura mín. 80% para protocolo |
| 8 | **Documentação de setup** | Criar README.md com instruções de instalação, build, execução e teste. Incluir pré-requisitos. | README completo e funcional |

---

## 3. Dependências

| Tarefa | Depende de |
|--------|------------|
| 2 (ProtocolHandler) | 1 (Setup do projeto) |
| 3 (Capability negotiation) | 2 (ProtocolHandler) |
| 4 (ResourceRegistry) | 2 (ProtocolHandler) |
| 5 (ToolExecutor) | 2 (ProtocolHandler) |
| 6 (Error handling) | 2 (ProtocolHandler) |
| 7 (Testes) | 4, 5, 6 |
| 8 (Documentação) | 1, 2, 3 |

**Grafo de dependências:**

```
[1] Setup
 └──→ [2] ProtocolHandler
       ├──→ [3] Capability Negotiation
       ├──→ [4] ResourceRegistry ──→ [7] Testes
       ├──→ [5] ToolExecutor ─────→ [7] Testes
       └──→ [6] Error Handling ───→ [7] Testes
 └──→ [8] Documentação (parcial, finalizada após 3)
```

---

## 4. Outputs Esperados

| Artefato | Localização |
|----------|-------------|
| Código-fonte do servidor | `src/atlas_mcp/` |
| Configuração do projeto | `pyproject.toml` |
| Configuração de lint/format | `ruff.toml` |
| Lock file | `uv.lock` |
| Testes unitários | `tests/` |
| Documentação | `README.md` |
| Entry point | `src/atlas_mcp/__main__.py` |

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
│   ├── test_handler.py
│   ├── test_registry.py
│   └── test_executor.py
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
| 10 | README contém instruções suficientes para execução independente | Revisão manual |

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

---

## 8. Observações

- Esta fase **não** inclui banco de dados, vetorização ou governança funcional. Esses são escopo das Fases 2, 3 e 4.
- O resource `context://core/stack` e a tool `search_context` usam **dados mock** nesta fase. Serão conectados a dados reais na Fase 2.
- O servidor utiliza **transporte stdio** por padrão, conforme recomendado pela spec MCP para desenvolvimento local.

---

> **Próximo passo:** Este documento deve ser revisado e aprovado antes do início da implementação.
