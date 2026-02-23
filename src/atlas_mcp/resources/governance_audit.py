"""Resource: context://governance/audit-log — Governance audit trail."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

_AUDIT_LOG_URI = "context://governance/audit-log"
_AUDIT_LOG_NAME = "governance_audit_log"
_AUDIT_LOG_DESCRIPTION = "Governance audit trail — recent document lifecycle events"


def register_governance_audit(server: FastMCP) -> None:
    """Register the ``context://governance/audit-log`` resource.

    Returns recent audit log entries. When no database is available,
    returns a placeholder message.

    Args:
        server: The FastMCP server instance to register on.
    """

    @server.resource(
        _AUDIT_LOG_URI,
        name=_AUDIT_LOG_NAME,
        description=_AUDIT_LOG_DESCRIPTION,
        mime_type="application/json",
    )
    def governance_audit_log() -> str:
        """Return recent audit log entries as JSON.

        When no database connection is available, returns a status
        message indicating the audit log is offline.
        """
        return json.dumps(
            {
                "status": "offline",
                "message": "Audit log requires database connection. "
                "Use GovernanceService with a DatabaseManager for live audit data.",
                "entries": [],
            },
            indent=2,
        )

    logger.info("Registered resource %s", _AUDIT_LOG_URI)
