# P2-D5 — Governance Model

**Branch:** `FET/P2-D5`
**Tipo:** `FET`
**Depende de:** D2 (Persistence Layer)

---

## Objetivo

Implementar o modelo de governança de documentos com:

1. **GovernanceService** — gerencia ciclo de vida `PROPOSED → IN_REVIEW → APPROVED → DEPRECATED` (e `REJECTED`)
2. **AuditLogger** — registra transições de estado na tabela `audit_log`
3. **Resource `context://governance/audit-log`** — expõe log de auditoria via MCP

## Design

### DocumentStatus (Enum)

```
PROPOSED → IN_REVIEW → APPROVED → DEPRECATED
                    ↘ REJECTED
```

Transições válidas:
- PROPOSED → IN_REVIEW
- IN_REVIEW → APPROVED
- IN_REVIEW → REJECTED
- APPROVED → DEPRECATED

### GovernanceService

- `create_document(title, content, doc_type, metadata?)` — cria com status PROPOSED
- `transition(document_id, new_status, details?)` — valida e executa transição
- `get_document(document_id)` — retorna documento
- `list_documents(status?, doc_type?)` — filtra documentos

### AuditLogger

- `log(entity_type, entity_id, action, old_status?, new_status?, details?)` — insere na audit_log
- `get_entries(entity_type?, entity_id?, limit?)` — consulta log

### Resource

- `context://governance/audit-log` — retorna últimas N entradas do audit_log

## Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `src/atlas_mcp/governance/service.py` | GovernanceService + DocumentStatus |
| `src/atlas_mcp/governance/audit.py` | AuditLogger |
| `src/atlas_mcp/resources/governance_audit.py` | Resource MCP |
| `tests/unit/test_governance_service.py` | Testes do GovernanceService |
| `tests/unit/test_audit_logger.py` | Testes do AuditLogger |

## Nota

Como D5 é unit test only (sem DB real), os testes usam mocks do DatabaseManager/pool.
O resource de audit-log opera de forma offline (mock) quando não há DB disponível.
