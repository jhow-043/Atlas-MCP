"""Document governance and lifecycle management.

Provides status tracking with validated transitions and
audit logging for all state changes.
"""

from __future__ import annotations

import enum
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from atlas_mcp.governance.audit import AuditLogger
    from atlas_mcp.persistence.database import DatabaseManager

logger = logging.getLogger(__name__)


class DocumentStatus(enum.Enum):
    """Lifecycle states for governed documents.

    Transition graph::

        PROPOSED → IN_REVIEW → APPROVED → DEPRECATED
                            ↘ REJECTED
    """

    PROPOSED = "PROPOSED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DEPRECATED = "DEPRECATED"


#: Allowed state transitions keyed by current status.
VALID_TRANSITIONS: dict[DocumentStatus, set[DocumentStatus]] = {
    DocumentStatus.PROPOSED: {DocumentStatus.IN_REVIEW},
    DocumentStatus.IN_REVIEW: {DocumentStatus.APPROVED, DocumentStatus.REJECTED},
    DocumentStatus.APPROVED: {DocumentStatus.DEPRECATED},
    DocumentStatus.REJECTED: set(),
    DocumentStatus.DEPRECATED: set(),
}


class InvalidTransitionError(Exception):
    """Raised when a status transition is not allowed.

    Attributes:
        current_status: The current status of the document.
        target_status: The attempted target status.
    """

    def __init__(self, current_status: DocumentStatus, target_status: DocumentStatus) -> None:
        """Initialize with current and target statuses.

        Args:
            current_status: The current status of the document.
            target_status: The attempted target status.
        """
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(f"Invalid transition: {current_status.value} → {target_status.value}")


class DocumentNotFoundError(Exception):
    """Raised when a document ID does not exist.

    Attributes:
        document_id: The missing document ID.
    """

    def __init__(self, document_id: int) -> None:
        """Initialize with the missing document ID.

        Args:
            document_id: The ID that was not found.
        """
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}")


class GovernanceService:
    """Manage document lifecycle with validated transitions and audit logging.

    All state changes are persisted to PostgreSQL via the provided
    ``DatabaseManager`` and recorded by the ``AuditLogger``.

    Args:
        db: The database manager for persistence.
        audit_logger: The audit logger for recording transitions.
    """

    def __init__(self, db: DatabaseManager, audit_logger: AuditLogger) -> None:
        """Initialize with database manager and audit logger.

        Args:
            db: The database manager for persistence.
            audit_logger: The audit logger for recording transitions.
        """
        self._db = db
        self._audit = audit_logger

    async def create_document(
        self,
        title: str,
        content: str,
        doc_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new governed document with status PROPOSED.

        Args:
            title: The document title.
            content: The document body content.
            doc_type: Type classification (e.g. ``'adr'``, ``'rfc'``).
            metadata: Optional JSON-serializable metadata.

        Returns:
            A dictionary with the created document fields.

        Raises:
            ValueError: If title or content is empty.
        """
        if not title.strip():
            raise ValueError("title cannot be empty")
        if not content.strip():
            raise ValueError("content cannot be empty")

        import json

        meta_json = json.dumps(metadata or {})

        row = await self._db.fetchrow(
            """
            INSERT INTO documents (title, content, doc_type, status, version, metadata)
            VALUES ($1, $2, $3, $4, 1, $5::jsonb)
            RETURNING id, title, content, doc_type, status, version,
                      metadata, created_at, updated_at
            """,
            title,
            content,
            doc_type,
            DocumentStatus.PROPOSED.value,
            meta_json,
        )

        if row is None:  # pragma: no cover
            msg = "Failed to create document"
            raise RuntimeError(msg)

        doc = dict(row)
        logger.info("Created document #%d: %s (type=%s)", doc["id"], title, doc_type)

        await self._audit.log(
            entity_type="document",
            entity_id=doc["id"],
            action="CREATE",
            new_status=DocumentStatus.PROPOSED.value,
            details={"title": title, "doc_type": doc_type},
        )

        return doc

    async def transition(
        self,
        document_id: int,
        new_status: DocumentStatus,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Transition a document to a new status.

        Validates the transition against :data:`VALID_TRANSITIONS`
        before applying.

        Args:
            document_id: The document ID to transition.
            new_status: The target status.
            details: Optional context about the transition.

        Returns:
            The updated document as a dictionary.

        Raises:
            DocumentNotFoundError: If the document does not exist.
            InvalidTransitionError: If the transition is not allowed.
        """
        row = await self._db.fetchrow(
            "SELECT id, status FROM documents WHERE id = $1",
            document_id,
        )

        if row is None:
            raise DocumentNotFoundError(document_id)

        current_status = DocumentStatus(row["status"])
        allowed = VALID_TRANSITIONS.get(current_status, set())

        if new_status not in allowed:
            raise InvalidTransitionError(current_status, new_status)

        updated = await self._db.fetchrow(
            """
            UPDATE documents
            SET status = $1, updated_at = NOW()
            WHERE id = $2
            RETURNING id, title, content, doc_type, status, version,
                      metadata, created_at, updated_at
            """,
            new_status.value,
            document_id,
        )

        if updated is None:  # pragma: no cover
            msg = f"Failed to update document {document_id}"
            raise RuntimeError(msg)

        doc = dict(updated)
        logger.info(
            "Document #%d transitioned: %s → %s",
            document_id,
            current_status.value,
            new_status.value,
        )

        await self._audit.log(
            entity_type="document",
            entity_id=document_id,
            action="TRANSITION",
            old_status=current_status.value,
            new_status=new_status.value,
            details=details or {},
        )

        return doc

    async def get_document(self, document_id: int) -> dict[str, Any]:
        """Retrieve a single document by ID.

        Args:
            document_id: The document ID.

        Returns:
            The document as a dictionary.

        Raises:
            DocumentNotFoundError: If the document does not exist.
        """
        row = await self._db.fetchrow(
            """
            SELECT id, title, content, doc_type, status, version,
                   metadata, created_at, updated_at
            FROM documents WHERE id = $1
            """,
            document_id,
        )

        if row is None:
            raise DocumentNotFoundError(document_id)

        return dict(row)

    async def list_documents(
        self,
        status: DocumentStatus | None = None,
        doc_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """List documents with optional filters.

        Args:
            status: Filter by document status.
            doc_type: Filter by document type.

        Returns:
            A list of document dictionaries.
        """
        query = "SELECT id, title, doc_type, status, version, created_at, updated_at FROM documents"
        conditions: list[str] = []
        params: list[Any] = []

        if status is not None:
            params.append(status.value)
            conditions.append(f"status = ${len(params)}")

        if doc_type is not None:
            params.append(doc_type)
            conditions.append(f"doc_type = ${len(params)}")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC"

        rows = await self._db.fetch(query, *params)
        return [dict(r) for r in rows]
