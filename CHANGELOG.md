# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Adicionado

- Estrutura inicial do repositório (Fase 0)
- Configuração do projeto Python com uv, Ruff, pytest e mypy
- Documentação base (README, CONTRIBUTING, LICENSE, CODE_OF_CONDUCT)
- Política de branching e governança de desenvolvimento
- Templates de issues e pull requests
- CI pipeline com GitHub Actions
- ADR-001: Uso de Python com SDK MCP oficial
- ADR-002: Uso de uv como gerenciador de pacotes
- **Fase 1:** Fundação e Protocolo MCP
  - ProtocolHandler com FastMCP e transporte stdio
  - Capability Negotiation
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

## [0.0.1] - 2026-02-19

### Adicionado

- Bootstrap do repositório Atlas MCP
- Estrutura de diretórios do projeto

[Unreleased]: https://github.com/jhow-043/Atlas-MCP/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/jhow-043/Atlas-MCP/releases/tag/v0.0.1
