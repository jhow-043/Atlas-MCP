"""Resources: context://decisions/adrs and context://decisions/adrs/{id}."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from atlas_mcp.context.decision import DecisionContextProvider

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

_LIST_URI = "context://decisions/adrs"
_LIST_NAME = "decision_adrs_list"
_LIST_DESCRIPTION = "List of all Architecture Decision Records"

_DETAIL_URI = "context://decisions/adrs/{adr_id}"
_DETAIL_NAME = "decision_adr_detail"
_DETAIL_DESCRIPTION = "Full details of a specific Architecture Decision Record"


def register_decision_adrs(server: FastMCP) -> None:
    """Register decision ADR resources on *server*.

    Registers two resources:
    - ``context://decisions/adrs`` — summary list of all ADRs
    - ``context://decisions/adrs/{adr_id}`` — full details of one ADR

    Args:
        server: The FastMCP server instance to register on.
    """
    provider = DecisionContextProvider()

    @server.resource(
        _LIST_URI,
        name=_LIST_NAME,
        description=_LIST_DESCRIPTION,
        mime_type="application/json",
    )
    def decision_adrs_list() -> str:
        """Return summary list of all ADRs as JSON."""
        return json.dumps(provider.list_adrs(), indent=2)

    @server.resource(
        _DETAIL_URI,
        name=_DETAIL_NAME,
        description=_DETAIL_DESCRIPTION,
        mime_type="application/json",
    )
    def decision_adr_detail(adr_id: int) -> str:
        """Return full details of a specific ADR.

        Args:
            adr_id: The ADR number to retrieve.

        Returns:
            JSON string with ADR details, or error message.
        """
        result = provider.get_adr(adr_id)
        if result is None:
            return json.dumps({"error": f"ADR-{adr_id:03d} not found"})
        return json.dumps(result, indent=2)

    logger.info("Registered resources %s and %s", _LIST_URI, _DETAIL_URI)
