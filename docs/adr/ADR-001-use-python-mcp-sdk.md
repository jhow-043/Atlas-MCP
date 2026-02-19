# ADR-001: Uso de Python com SDK MCP Oficial

**Data:** 2026-02-19  
**Status:** APPROVED  
**Autor:** jhow-043  
**Tags:** linguagem, runtime, sdk, mcp

---

### Contexto

O projeto Atlas MCP precisa de uma linguagem de programação para implementar o servidor MCP. As duas opções principais eram **TypeScript** (com `@modelcontextprotocol/sdk`) e **Python** (com `mcp`, o SDK oficial Python).

O projeto envolve integração com banco vetorial (pgvector), pipelines de embedding e RAG — áreas onde o ecossistema Python é significativamente mais maduro.

A equipe tem preferência e maior proficiência em Python.

### Decisão

Adotar **Python ≥ 3.12** como linguagem principal do projeto, utilizando o SDK oficial `mcp` para implementação do servidor MCP.

### Alternativas Consideradas

| Alternativa | Prós | Contras |
|-------------|------|---------|
| **TypeScript + `@modelcontextprotocol/sdk`** | SDK mais maduro, ampla adoção na comunidade MCP, tipagem estática nativa | Ecossistema ML/RAG menos maduro, menor familiaridade da equipe |
| **Python + `mcp`** | Ecossistema ML/RAG maduro (numpy, scikit, langchain), SDK oficial disponível, preferência da equipe, type hints com mypy | SDK Python pode ser menos documentado |

### Consequências

**Positivas:**
- Acesso direto a bibliotecas de ML/RAG maduras (numpy, psycopg, etc.)
- Maior produtividade da equipe
- Tipagem estática via mypy + type hints
- Integração natural com ferramentas de embedding e banco vetorial

**Negativas:**
- Performance inferior ao TypeScript para I/O intensivo (mitigável com asyncio)
- SDK Python pode ter menos exemplos na comunidade

**Riscos:**
- SDK Python `mcp` pode ter breaking changes — mitigação: fixar versão no `pyproject.toml`

---

### Referências

- [Model Context Protocol — GitHub](https://github.com/modelcontextprotocol)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
