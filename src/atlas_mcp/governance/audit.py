"""Audit logging for governance actions.

Records all state changes and significant events into the
``audit_log`` database table.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from atlas_mcp.persistence.database import DatabaseManager

logger = logging.getLogger(__name__)


class AuditLogger:
    """Persist audit entries to the ``audit_log`` table.

    Every governance action (document creation, status transition,
    etc.) should be recorded via this logger for traceability.

    Args:
        db: The database manager for persistence.
    """

    def __init__(self, db: DatabaseManager) -> None:
        """Initialize with database manager.

        Args:
            db: The database manager for persistence.
        """
        self._db = db

    async def log(
        self,
        entity_type: str,
        entity_id: int,
        action: str,
        old_status: str | None = None,
        new_status: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> int:
        """Record an audit entry.

        Args:
            entity_type: The type of entity (e.g. ``'document'``).
            entity_id: The entity's primary key.
            action: The action performed (e.g. ``'CREATE'``, ``'TRANSITION'``).
            old_status: The previous status, if applicable.
            new_status: The new status, if applicable.
            details: Optional JSON-serializable context.

        Returns:
            The ID of the created audit log entry.
        """
        import json

        details_json = json.dumps(details or {})

        entry_id: int = await self._db.fetchval(
            """
            INSERT INTO audit_log
                (entity_type, entity_id, action, old_status, new_status, details)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            RETURNING id
            """,
            entity_type,
            entity_id,
            action,
            old_status,
            new_status,
            details_json,
        )

        logger.info(
            "Audit log #%d: %s %s#%d (%s → %s)",
            entry_id,
            action,
            entity_type,
            entity_id,
            old_status or "-",
            new_status or "-",
        )

        return entry_id

    async def get_entries(
        self,
        entity_type: str | None = None,
        entity_id: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Retrieve audit log entries with optional filters.

        Args:
            entity_type: Filter by entity type.
            entity_id: Filter by entity ID (requires entity_type).
            limit: Maximum number of entries to return.

        Returns:
            A list of audit log entry dictionaries.
        """
        query = (
            "SELECT id, entity_type, entity_id, action, "
            "old_status, new_status, details, created_at "
            "FROM audit_log"
        )
        conditions: list[str] = []
        params: list[Any] = []

        if entity_type is not None:
            params.append(entity_type)
            conditions.append(f"entity_type = ${len(params)}")

        if entity_id is not None:
            params.append(entity_id)
            conditions.append(f"entity_id = ${len(params)}")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        params.append(limit)
        query += f" ORDER BY created_at DESC LIMIT ${len(params)}"

        rows = await self._db.fetch(query, *params)
        return [dict(r) for r in rows]
