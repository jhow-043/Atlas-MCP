"""Tests for the AuditLogger module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from atlas_mcp.governance.audit import AuditLogger

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(
    fetchval_return: Any = 1,
    fetch_return: Any = None,
) -> MagicMock:
    """Build a mock DatabaseManager."""
    db = MagicMock()
    db.fetchval = AsyncMock(return_value=fetchval_return)
    db.fetch = AsyncMock(return_value=fetch_return or [])
    return db


def _make_row(**kwargs: Any) -> dict[str, Any]:
    """Create a dict simulating an asyncpg.Record."""
    return dict(kwargs)


# ---------------------------------------------------------------------------
# AuditLogger.log tests
# ---------------------------------------------------------------------------


class TestAuditLoggerLog:
    """Tests for AuditLogger.log."""

    async def test_should_insert_audit_entry(self) -> None:
        db = _make_db(fetchval_return=42)
        logger = AuditLogger(db)

        entry_id = await logger.log(
            entity_type="document",
            entity_id=1,
            action="CREATE",
            new_status="PROPOSED",
        )

        assert entry_id == 42
        db.fetchval.assert_awaited_once()

    async def test_should_include_old_and_new_status(self) -> None:
        db = _make_db()
        logger = AuditLogger(db)

        await logger.log(
            entity_type="document",
            entity_id=1,
            action="TRANSITION",
            old_status="PROPOSED",
            new_status="IN_REVIEW",
        )

        call_args = db.fetchval.call_args
        assert "INSERT INTO audit_log" in call_args.args[0]
        assert call_args.args[4] == "PROPOSED"
        assert call_args.args[5] == "IN_REVIEW"

    async def test_should_handle_none_statuses(self) -> None:
        db = _make_db()
        logger = AuditLogger(db)

        await logger.log(
            entity_type="document",
            entity_id=1,
            action="DELETE",
        )

        call_args = db.fetchval.call_args
        assert call_args.args[4] is None
        assert call_args.args[5] is None

    async def test_should_serialize_details_as_json(self) -> None:
        db = _make_db()
        logger = AuditLogger(db)

        await logger.log(
            entity_type="document",
            entity_id=1,
            action="CREATE",
            details={"reason": "initial", "author": "bot"},
        )

        call_args = db.fetchval.call_args
        details_json = call_args.args[6]
        assert '"reason"' in details_json
        assert '"author"' in details_json

    async def test_should_default_details_to_empty_json(self) -> None:
        db = _make_db()
        logger = AuditLogger(db)

        await logger.log(
            entity_type="document",
            entity_id=1,
            action="CREATE",
        )

        call_args = db.fetchval.call_args
        assert call_args.args[6] == "{}"

    async def test_should_return_entry_id(self) -> None:
        db = _make_db(fetchval_return=7)
        logger = AuditLogger(db)

        result = await logger.log(
            entity_type="document",
            entity_id=1,
            action="CREATE",
        )

        assert result == 7


# ---------------------------------------------------------------------------
# AuditLogger.get_entries tests
# ---------------------------------------------------------------------------


class TestAuditLoggerGetEntries:
    """Tests for AuditLogger.get_entries."""

    async def test_should_return_all_entries_with_default_limit(self) -> None:
        rows = [
            _make_row(
                id=1,
                entity_type="document",
                entity_id=1,
                action="CREATE",
                old_status=None,
                new_status="PROPOSED",
                details={},
                created_at="2026-01-01T00:00:00Z",
            ),
        ]
        db = _make_db(fetch_return=rows)
        logger = AuditLogger(db)

        entries = await logger.get_entries()
        assert len(entries) == 1
        call_args = db.fetch.call_args
        assert "LIMIT $1" in call_args.args[0]
        assert call_args.args[1] == 50

    async def test_should_filter_by_entity_type(self) -> None:
        db = _make_db(fetch_return=[])
        logger = AuditLogger(db)

        await logger.get_entries(entity_type="document")
        call_args = db.fetch.call_args
        assert "entity_type = $1" in call_args.args[0]
        assert call_args.args[1] == "document"

    async def test_should_filter_by_entity_id(self) -> None:
        db = _make_db(fetch_return=[])
        logger = AuditLogger(db)

        await logger.get_entries(entity_id=5)
        call_args = db.fetch.call_args
        assert "entity_id = $1" in call_args.args[0]
        assert call_args.args[1] == 5

    async def test_should_filter_by_type_and_id(self) -> None:
        db = _make_db(fetch_return=[])
        logger = AuditLogger(db)

        await logger.get_entries(entity_type="document", entity_id=3)
        call_args = db.fetch.call_args
        assert "entity_type = $1" in call_args.args[0]
        assert "entity_id = $2" in call_args.args[0]
        assert call_args.args[1] == "document"
        assert call_args.args[2] == 3

    async def test_should_respect_custom_limit(self) -> None:
        db = _make_db(fetch_return=[])
        logger = AuditLogger(db)

        await logger.get_entries(limit=10)
        call_args = db.fetch.call_args
        assert call_args.args[1] == 10

    async def test_should_return_empty_list(self) -> None:
        db = _make_db(fetch_return=[])
        logger = AuditLogger(db)

        entries = await logger.get_entries()
        assert entries == []

    async def test_should_order_by_created_at_desc(self) -> None:
        db = _make_db(fetch_return=[])
        logger = AuditLogger(db)

        await logger.get_entries()
        call_args = db.fetch.call_args
        assert "ORDER BY created_at DESC" in call_args.args[0]
