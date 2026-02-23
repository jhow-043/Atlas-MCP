"""Tests for the GovernanceService module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from atlas_mcp.governance.service import (
    VALID_TRANSITIONS,
    DocumentNotFoundError,
    DocumentStatus,
    GovernanceService,
    InvalidTransitionError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(
    fetchrow_return: Any = None,
    fetch_return: Any = None,
) -> MagicMock:
    """Build a mock DatabaseManager."""
    db = MagicMock()
    db.fetchrow = AsyncMock(return_value=fetchrow_return)
    db.fetchval = AsyncMock(return_value=1)
    db.fetch = AsyncMock(return_value=fetch_return or [])
    db.execute = AsyncMock(return_value="OK")
    return db


def _make_audit() -> MagicMock:
    """Build a mock AuditLogger."""
    audit = MagicMock()
    audit.log = AsyncMock(return_value=1)
    return audit


def _make_row(**kwargs: Any) -> MagicMock:
    """Create a mock asyncpg.Record-like object."""
    row = MagicMock()
    row.__getitem__ = lambda self, key: kwargs[key]
    row.__iter__ = lambda self: iter(kwargs)
    row.keys = lambda: kwargs.keys()

    def _row_dict() -> dict[str, Any]:
        return dict(kwargs)

    # When dict(row) is called, Python uses __iter__ + __getitem__
    # But for our mocks it's simpler to mock items()
    row.items = lambda: kwargs.items()
    row.__contains__ = lambda self, key: key in kwargs

    # Make dict(row) work
    class RowDict(dict[str, Any]):
        pass

    return RowDict(kwargs)


# ---------------------------------------------------------------------------
# DocumentStatus tests
# ---------------------------------------------------------------------------


class TestDocumentStatus:
    """Tests for the DocumentStatus enum."""

    def test_should_have_five_statuses(self) -> None:
        assert len(DocumentStatus) == 5

    def test_should_contain_all_expected_values(self) -> None:
        expected = {"PROPOSED", "IN_REVIEW", "APPROVED", "REJECTED", "DEPRECATED"}
        assert {s.value for s in DocumentStatus} == expected

    def test_should_create_from_string(self) -> None:
        assert DocumentStatus("PROPOSED") is DocumentStatus.PROPOSED
        assert DocumentStatus("APPROVED") is DocumentStatus.APPROVED


class TestValidTransitions:
    """Tests for the VALID_TRANSITIONS map."""

    def test_proposed_can_go_to_in_review(self) -> None:
        assert DocumentStatus.IN_REVIEW in VALID_TRANSITIONS[DocumentStatus.PROPOSED]

    def test_in_review_can_go_to_approved_or_rejected(self) -> None:
        allowed = VALID_TRANSITIONS[DocumentStatus.IN_REVIEW]
        assert DocumentStatus.APPROVED in allowed
        assert DocumentStatus.REJECTED in allowed

    def test_approved_can_go_to_deprecated(self) -> None:
        assert DocumentStatus.DEPRECATED in VALID_TRANSITIONS[DocumentStatus.APPROVED]

    def test_rejected_has_no_transitions(self) -> None:
        assert VALID_TRANSITIONS[DocumentStatus.REJECTED] == set()

    def test_deprecated_has_no_transitions(self) -> None:
        assert VALID_TRANSITIONS[DocumentStatus.DEPRECATED] == set()

    def test_every_status_has_transition_entry(self) -> None:
        for status in DocumentStatus:
            assert status in VALID_TRANSITIONS


# ---------------------------------------------------------------------------
# InvalidTransitionError tests
# ---------------------------------------------------------------------------


class TestInvalidTransitionError:
    """Tests for the InvalidTransitionError exception."""

    def test_should_contain_statuses_in_message(self) -> None:
        err = InvalidTransitionError(DocumentStatus.PROPOSED, DocumentStatus.APPROVED)
        assert "PROPOSED" in str(err)
        assert "APPROVED" in str(err)

    def test_should_store_status_attributes(self) -> None:
        err = InvalidTransitionError(DocumentStatus.REJECTED, DocumentStatus.PROPOSED)
        assert err.current_status is DocumentStatus.REJECTED
        assert err.target_status is DocumentStatus.PROPOSED


class TestDocumentNotFoundError:
    """Tests for the DocumentNotFoundError exception."""

    def test_should_contain_id_in_message(self) -> None:
        err = DocumentNotFoundError(42)
        assert "42" in str(err)

    def test_should_store_document_id(self) -> None:
        err = DocumentNotFoundError(99)
        assert err.document_id == 99


# ---------------------------------------------------------------------------
# GovernanceService.create_document tests
# ---------------------------------------------------------------------------


class TestGovernanceServiceCreate:
    """Tests for GovernanceService.create_document."""

    @pytest.fixture()
    def service(self) -> GovernanceService:
        row = _make_row(
            id=1,
            title="Test Doc",
            content="Body",
            doc_type="adr",
            status="PROPOSED",
            version=1,
            metadata={},
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        db = _make_db(fetchrow_return=row)
        audit = _make_audit()
        return GovernanceService(db, audit)

    async def test_should_create_document_with_proposed_status(
        self, service: GovernanceService
    ) -> None:
        doc = await service.create_document("Test Doc", "Body", "adr")
        assert doc["status"] == "PROPOSED"
        assert doc["title"] == "Test Doc"

    async def test_should_call_audit_log_on_create(self, service: GovernanceService) -> None:
        await service.create_document("Test Doc", "Body", "adr")
        service._audit.log.assert_awaited_once()
        call_kwargs = service._audit.log.call_args.kwargs
        assert call_kwargs["action"] == "CREATE"
        assert call_kwargs["new_status"] == "PROPOSED"

    async def test_should_reject_empty_title(self, service: GovernanceService) -> None:
        with pytest.raises(ValueError, match="title"):
            await service.create_document("", "Body", "adr")

    async def test_should_reject_blank_title(self, service: GovernanceService) -> None:
        with pytest.raises(ValueError, match="title"):
            await service.create_document("   ", "Content", "adr")

    async def test_should_reject_empty_content(self, service: GovernanceService) -> None:
        with pytest.raises(ValueError, match="content"):
            await service.create_document("Title", "", "adr")

    async def test_should_accept_metadata(self, service: GovernanceService) -> None:
        doc = await service.create_document("T", "C", "adr", metadata={"key": "val"})
        assert doc["id"] == 1

    async def test_should_insert_with_correct_sql(self, service: GovernanceService) -> None:
        await service.create_document("Title", "Content", "rfc")
        call_args = service._db.fetchrow.call_args
        assert "INSERT INTO documents" in call_args.args[0]
        assert call_args.args[1] == "Title"
        assert call_args.args[2] == "Content"
        assert call_args.args[3] == "rfc"


# ---------------------------------------------------------------------------
# GovernanceService.transition tests
# ---------------------------------------------------------------------------


class TestGovernanceServiceTransition:
    """Tests for GovernanceService.transition."""

    async def test_should_transition_proposed_to_in_review(self) -> None:
        current_row = _make_row(id=1, status="PROPOSED")
        updated_row = _make_row(
            id=1,
            title="Doc",
            content="Body",
            doc_type="adr",
            status="IN_REVIEW",
            version=1,
            metadata={},
            created_at="2026-01-01",
            updated_at="2026-01-02",
        )
        db = _make_db()
        db.fetchrow = AsyncMock(side_effect=[current_row, updated_row])
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        doc = await svc.transition(1, DocumentStatus.IN_REVIEW)
        assert doc["status"] == "IN_REVIEW"

    async def test_should_transition_in_review_to_approved(self) -> None:
        current_row = _make_row(id=1, status="IN_REVIEW")
        updated_row = _make_row(
            id=1,
            title="D",
            content="B",
            doc_type="adr",
            status="APPROVED",
            version=1,
            metadata={},
            created_at="2026-01-01",
            updated_at="2026-01-02",
        )
        db = _make_db()
        db.fetchrow = AsyncMock(side_effect=[current_row, updated_row])
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        doc = await svc.transition(1, DocumentStatus.APPROVED)
        assert doc["status"] == "APPROVED"

    async def test_should_reject_invalid_transition(self) -> None:
        current_row = _make_row(id=1, status="PROPOSED")
        db = _make_db(fetchrow_return=current_row)
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        with pytest.raises(InvalidTransitionError):
            await svc.transition(1, DocumentStatus.APPROVED)

    async def test_should_raise_not_found_for_missing_document(self) -> None:
        db = _make_db(fetchrow_return=None)
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        with pytest.raises(DocumentNotFoundError):
            await svc.transition(999, DocumentStatus.IN_REVIEW)

    async def test_should_log_audit_on_transition(self) -> None:
        current_row = _make_row(id=1, status="IN_REVIEW")
        updated_row = _make_row(
            id=1,
            title="D",
            content="B",
            doc_type="adr",
            status="REJECTED",
            version=1,
            metadata={},
            created_at="2026-01-01",
            updated_at="2026-01-02",
        )
        db = _make_db()
        db.fetchrow = AsyncMock(side_effect=[current_row, updated_row])
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        await svc.transition(1, DocumentStatus.REJECTED, details={"reason": "scope"})
        audit.log.assert_awaited_once()
        kwargs = audit.log.call_args.kwargs
        assert kwargs["action"] == "TRANSITION"
        assert kwargs["old_status"] == "IN_REVIEW"
        assert kwargs["new_status"] == "REJECTED"

    async def test_should_reject_transition_from_rejected(self) -> None:
        current_row = _make_row(id=1, status="REJECTED")
        db = _make_db(fetchrow_return=current_row)
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        with pytest.raises(InvalidTransitionError):
            await svc.transition(1, DocumentStatus.PROPOSED)

    async def test_should_reject_transition_from_deprecated(self) -> None:
        current_row = _make_row(id=1, status="DEPRECATED")
        db = _make_db(fetchrow_return=current_row)
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        with pytest.raises(InvalidTransitionError):
            await svc.transition(1, DocumentStatus.APPROVED)

    async def test_should_transition_approved_to_deprecated(self) -> None:
        current_row = _make_row(id=1, status="APPROVED")
        updated_row = _make_row(
            id=1,
            title="D",
            content="B",
            doc_type="adr",
            status="DEPRECATED",
            version=1,
            metadata={},
            created_at="2026-01-01",
            updated_at="2026-01-02",
        )
        db = _make_db()
        db.fetchrow = AsyncMock(side_effect=[current_row, updated_row])
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        doc = await svc.transition(1, DocumentStatus.DEPRECATED)
        assert doc["status"] == "DEPRECATED"


# ---------------------------------------------------------------------------
# GovernanceService.get_document tests
# ---------------------------------------------------------------------------


class TestGovernanceServiceGetDocument:
    """Tests for GovernanceService.get_document."""

    async def test_should_return_document_by_id(self) -> None:
        row = _make_row(
            id=5,
            title="My ADR",
            content="Content",
            doc_type="adr",
            status="APPROVED",
            version=2,
            metadata={},
            created_at="2026-01-01",
            updated_at="2026-01-02",
        )
        db = _make_db(fetchrow_return=row)
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        doc = await svc.get_document(5)
        assert doc["id"] == 5
        assert doc["title"] == "My ADR"

    async def test_should_raise_not_found(self) -> None:
        db = _make_db(fetchrow_return=None)
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        with pytest.raises(DocumentNotFoundError):
            await svc.get_document(999)


# ---------------------------------------------------------------------------
# GovernanceService.list_documents tests
# ---------------------------------------------------------------------------


class TestGovernanceServiceListDocuments:
    """Tests for GovernanceService.list_documents."""

    async def test_should_return_all_documents(self) -> None:
        rows = [
            _make_row(
                id=1,
                title="A",
                doc_type="adr",
                status="PROPOSED",
                version=1,
                created_at="2026-01-01",
                updated_at="2026-01-01",
            ),
            _make_row(
                id=2,
                title="B",
                doc_type="rfc",
                status="APPROVED",
                version=1,
                created_at="2026-01-02",
                updated_at="2026-01-02",
            ),
        ]
        db = _make_db(fetch_return=rows)
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        docs = await svc.list_documents()
        assert len(docs) == 2

    async def test_should_filter_by_status(self) -> None:
        db = _make_db(fetch_return=[])
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        await svc.list_documents(status=DocumentStatus.APPROVED)
        call_args = db.fetch.call_args
        assert "status = $1" in call_args.args[0]
        assert call_args.args[1] == "APPROVED"

    async def test_should_filter_by_doc_type(self) -> None:
        db = _make_db(fetch_return=[])
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        await svc.list_documents(doc_type="adr")
        call_args = db.fetch.call_args
        assert "doc_type = $1" in call_args.args[0]
        assert call_args.args[1] == "adr"

    async def test_should_filter_by_status_and_doc_type(self) -> None:
        db = _make_db(fetch_return=[])
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        await svc.list_documents(status=DocumentStatus.PROPOSED, doc_type="rfc")
        call_args = db.fetch.call_args
        assert "status = $1" in call_args.args[0]
        assert "doc_type = $2" in call_args.args[0]

    async def test_should_return_empty_list(self) -> None:
        db = _make_db(fetch_return=[])
        audit = _make_audit()
        svc = GovernanceService(db, audit)

        docs = await svc.list_documents()
        assert docs == []
