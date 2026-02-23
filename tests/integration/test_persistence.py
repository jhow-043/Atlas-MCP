"""Integration tests for the persistence layer.

These tests require a running PostgreSQL instance.
Run ``docker compose up -d`` and set env vars before executing.
"""

from __future__ import annotations

from atlas_mcp.persistence.config import DatabaseConfig
from tests.integration.conftest import requires_db


@requires_db
class TestDatabaseManagerIntegration:
    """Integration tests for DatabaseManager with real PostgreSQL."""

    async def test_should_connect_and_health_check(self) -> None:
        config = DatabaseConfig.from_env()
        from atlas_mcp.persistence.database import DatabaseManager

        async with DatabaseManager(config) as db:
            result = await db.health_check()
            assert result["status"] == "healthy"
            assert "server_version" in result

    async def test_should_execute_query(self) -> None:
        config = DatabaseConfig.from_env()
        from atlas_mcp.persistence.database import DatabaseManager

        async with DatabaseManager(config) as db:
            val = await db.fetchval("SELECT 1")
            assert val == 1

    async def test_should_run_migrations(self) -> None:
        config = DatabaseConfig.from_env()
        from atlas_mcp.persistence.database import DatabaseManager
        from atlas_mcp.persistence.migrations import MigrationRunner

        async with DatabaseManager(config) as db:
            runner = MigrationRunner(db.pool)
            applied = await runner.run()
            assert isinstance(applied, list)

            status = await runner.get_status()
            assert all(m["applied"] for m in status)


@requires_db
class TestGovernanceIntegration:
    """Integration tests for GovernanceService with real PostgreSQL."""

    async def test_should_create_and_transition_document(self) -> None:
        config = DatabaseConfig.from_env()
        from atlas_mcp.governance.audit import AuditLogger
        from atlas_mcp.governance.service import DocumentStatus, GovernanceService
        from atlas_mcp.persistence.database import DatabaseManager
        from atlas_mcp.persistence.migrations import MigrationRunner

        async with DatabaseManager(config) as db:
            runner = MigrationRunner(db.pool)
            await runner.run()

            audit = AuditLogger(db)
            svc = GovernanceService(db, audit)

            doc = await svc.create_document(
                title="Integration Test ADR",
                content="Test content for integration",
                doc_type="adr",
            )
            assert doc["status"] == "PROPOSED"

            doc = await svc.transition(doc["id"], DocumentStatus.IN_REVIEW)
            assert doc["status"] == "IN_REVIEW"

            doc = await svc.transition(doc["id"], DocumentStatus.APPROVED)
            assert doc["status"] == "APPROVED"

    async def test_should_list_audit_entries(self) -> None:
        config = DatabaseConfig.from_env()
        from atlas_mcp.governance.audit import AuditLogger
        from atlas_mcp.governance.service import GovernanceService
        from atlas_mcp.persistence.database import DatabaseManager
        from atlas_mcp.persistence.migrations import MigrationRunner

        async with DatabaseManager(config) as db:
            runner = MigrationRunner(db.pool)
            await runner.run()

            audit = AuditLogger(db)
            svc = GovernanceService(db, audit)

            await svc.create_document(
                title="Audit Test",
                content="Content",
                doc_type="rfc",
            )

            entries = await audit.get_entries(entity_type="document")
            assert len(entries) >= 1
            assert entries[0]["action"] in {"CREATE", "TRANSITION"}
