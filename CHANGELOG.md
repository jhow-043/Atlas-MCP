# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

## [0.1.0] - 2026-02-23

### Adicionado

- **Fase 0:** Fundação do Repositório
  - Estrutura inicial do repositório
  - Configuração do projeto Python com uv, Ruff, pytest e mypy
  - Documentação base (README, CONTRIBUTING, LICENSE, CODE_OF_CONDUCT)
  - Política de branching e governança de desenvolvimento
  - Templates de issues e pull requests
  - CI pipeline com GitHub Actions
  - ADR-001: Uso de Python com SDK MCP oficial
  - ADR-002: Uso de uv como gerenciador de pacotes
- **Fase 1:** Fundação e Protocolo MCP
  - ProtocolHandler com FastMCP e transporte stdio
  - Capability Negotiation (`initialize`/`initialized`)
  - ResourceRegistry com resource `context://core/stack`
  - ToolExecutor com tool `search_context` (mock)
  - Error handling com exceções customizadas JSON-RPC 2.0
  - 114 testes unitários com 100% de cobertura
- **Fase 2:** Context Layers e Infraestrutura de Persistência
  - Docker Compose com PostgreSQL 16 + pgvector
  - DatabaseManager com pool asyncpg e lifecycle
  - MigrationRunner com schema transacional (documents, audit_log)
  - ADR-003: Uso de asyncpg como driver PostgreSQL
  - CoreContextProvider — dados reais de pyproject.toml e ruff.toml
  - Resources `context://core/conventions` e `context://core/structure`
  - DecisionContextProvider — parser de ADRs Markdown
  - Resources `context://decisions/adrs` e `context://decisions/adrs/{id}`
  - GovernanceService com ciclo de vida PROPOSED → APPROVED → DEPRECATED
  - AuditLogger com persistência no audit_log
  - Resource `context://governance/audit-log`
  - WorkflowContextProvider com lifecycle e histórico
  - Resource `context://workflow/current`
  - Tool `register_adr` para criar ADRs via MCP
  - Testes de integração com PostgreSQL (requer Docker)
  - 319 testes, 97% de cobertura
- **Fase 3:** Vectorization, RAG e Tools Avançadas
  - pgvector Extension + Schema (migrations v5–v7) + codec asyncpg
  - ADR-004: Interface abstrata de Embedding Provider
  - `MarkdownChunker` — chunking semântico por headers com hierarquia
  - `EmbeddingProvider` (ABC) com OpenAI e Sentence Transformers
  - `VectorStore` — repositório pgvector com busca cosine + filtros
  - `IndexingService` — orquestrador chunk → embed → store
  - Hook `on_status_change` na GovernanceService (APPROVED→indexa, DEPRECATED→remove)
  - Tool `search_context` com pipeline RAG real (query→embed→search→format)
  - Tool `plan_feature` para planejamento estruturado de features com contexto
  - Tool `analyze_bug` para análise estruturada de bugs com contexto
  - Testes de integração E2E do pipeline de vectorização
  - Testes de integração governance → indexing
  - 510 testes, 96% de cobertura
- **Fase 4:** Bootstrap, Wiring e Servidor Funcional
  - `Settings` centralizado com leitura de `.env` via python-dotenv
  - Logging estruturado com formato text/json e output no stderr
  - `ApplicationBootstrap` com wiring completo e modo degradado
  - `__main__.py` com bootstrap async, graceful shutdown e suporte a transporte configurável
  - Dockerfile multi-stage e serviço atlas-mcp no docker-compose
  - Testes unitários para settings, logging, bootstrap e main
  - Testes de integração com pipeline completo contra PostgreSQL real
  - Smoke tests do servidor (in-memory e subprocess)
- **Fase 5:** Documentação, Hardening e Release v0.1.0
  - README.md reescrito com badges, Quick Start, API reference completa
  - Guia de configuração (`docs/configuration.md`)
  - Guia de uso com Claude Desktop e MCP Inspector (`docs/usage.md`)
  - Guia de deployment (`docs/deployment.md`)
  - CONTRIBUTING.md atualizado com setup Docker, testes e guia de extensão
  - CHANGELOG.md consolidado com todas as fases (0–4)
  - Hardening de validação de inputs nas tools
  - Testes de edge cases e validação robusta (81 cenários)
  - Version bump para `0.1.0` e Development Status `Alpha`

## [0.0.1] - 2026-02-19

### Adicionado

- Bootstrap do repositório Atlas MCP
- Estrutura de diretórios do projeto

[Unreleased]: https://github.com/jhow-043/Atlas-MCP/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jhow-043/Atlas-MCP/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/jhow-043/Atlas-MCP/releases/tag/v0.0.1
