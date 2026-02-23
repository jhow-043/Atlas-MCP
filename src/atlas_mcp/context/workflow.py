"""Workflow context management.

Tracks the currently active workflow (feature, bug, refactor)
and provides structured context for LLM agents about the
ongoing development activity.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class WorkflowType(enum.Enum):
    """Types of development workflows.

    Attributes:
        FEATURE: New feature development.
        BUG: Bug fix.
        REFACTOR: Code refactoring.
        DOCS: Documentation work.
        INFRA: Infrastructure changes.
    """

    FEATURE = "feature"
    BUG = "bug"
    REFACTOR = "refactor"
    DOCS = "docs"
    INFRA = "infra"


class WorkflowStatus(enum.Enum):
    """Lifecycle states for a workflow.

    Attributes:
        ACTIVE: Currently being worked on.
        PAUSED: Temporarily suspended.
        COMPLETED: Finished.
        CANCELLED: Abandoned.
    """

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowContext:
    """Represents a development workflow with metadata.

    Attributes:
        workflow_id: Unique identifier (e.g. ``'P2-D6'``).
        workflow_type: The type of workflow.
        title: Short description of the work.
        description: Detailed description.
        status: Current lifecycle status.
        branch: Git branch name.
        started_at: When the workflow was started.
        metadata: Additional context.
        history: List of status change events.
    """

    workflow_id: str
    workflow_type: WorkflowType
    title: str
    description: str = ""
    status: WorkflowStatus = WorkflowStatus.ACTIVE
    branch: str = ""
    started_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Set default started_at if not provided."""
        if not self.started_at:
            self.started_at = datetime.now(tz=UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary.

        Returns:
            A dictionary representation of the workflow.
        """
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type.value,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "branch": self.branch,
            "started_at": self.started_at,
            "metadata": self.metadata,
            "history": self.history,
        }


class WorkflowContextProvider:
    """Manage the active development workflow.

    Only one workflow can be active at a time. The provider tracks
    status transitions and maintains a history of changes.
    """

    def __init__(self) -> None:
        """Initialize with no active workflow."""
        self._current: WorkflowContext | None = None

    @property
    def current(self) -> WorkflowContext | None:
        """Return the current workflow, or ``None``.

        Returns:
            The active workflow context, or None if idle.
        """
        return self._current

    def start_workflow(
        self,
        workflow_id: str,
        workflow_type: WorkflowType,
        title: str,
        description: str = "",
        branch: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowContext:
        """Start a new workflow, replacing any existing one.

        If a workflow is already active, it will be completed
        automatically before starting the new one.

        Args:
            workflow_id: Unique identifier for the workflow.
            workflow_type: The type of workflow.
            title: Short description of the work.
            description: Detailed description.
            branch: Git branch name.
            metadata: Additional context.

        Returns:
            The newly created workflow context.

        Raises:
            ValueError: If workflow_id or title is empty.
        """
        if not workflow_id.strip():
            raise ValueError("workflow_id cannot be empty")
        if not title.strip():
            raise ValueError("title cannot be empty")

        if self._current is not None and self._current.status == WorkflowStatus.ACTIVE:
            logger.info(
                "Auto-completing workflow '%s' before starting '%s'",
                self._current.workflow_id,
                workflow_id,
            )
            self._transition(WorkflowStatus.COMPLETED, "Auto-completed by new workflow")

        workflow = WorkflowContext(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            title=title,
            description=description,
            branch=branch,
            metadata=metadata or {},
        )
        workflow.history.append(
            {
                "status": WorkflowStatus.ACTIVE.value,
                "timestamp": workflow.started_at,
                "reason": "Workflow started",
            }
        )

        self._current = workflow
        logger.info("Started workflow '%s': %s", workflow_id, title)
        return workflow

    def pause_workflow(self, reason: str = "") -> WorkflowContext:
        """Pause the active workflow.

        Args:
            reason: Optional reason for pausing.

        Returns:
            The updated workflow context.

        Raises:
            RuntimeError: If no active workflow exists.
        """
        self._ensure_active()
        return self._transition(WorkflowStatus.PAUSED, reason or "Paused")

    def resume_workflow(self, reason: str = "") -> WorkflowContext:
        """Resume a paused workflow.

        Args:
            reason: Optional reason for resuming.

        Returns:
            The updated workflow context.

        Raises:
            RuntimeError: If no workflow is paused.
        """
        if self._current is None:
            raise RuntimeError("No workflow to resume")
        if self._current.status != WorkflowStatus.PAUSED:
            raise RuntimeError(f"Cannot resume workflow in '{self._current.status.value}' status")
        return self._transition(WorkflowStatus.ACTIVE, reason or "Resumed")

    def complete_workflow(self, reason: str = "") -> WorkflowContext:
        """Complete the current workflow.

        Args:
            reason: Optional completion note.

        Returns:
            The completed workflow context.

        Raises:
            RuntimeError: If no active or paused workflow exists.
        """
        self._ensure_exists()
        if self._current is not None and self._current.status in {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.CANCELLED,
        }:
            raise RuntimeError(f"Cannot complete workflow in '{self._current.status.value}' status")
        return self._transition(WorkflowStatus.COMPLETED, reason or "Completed")

    def cancel_workflow(self, reason: str = "") -> WorkflowContext:
        """Cancel the current workflow.

        Args:
            reason: Optional cancellation reason.

        Returns:
            The cancelled workflow context.

        Raises:
            RuntimeError: If no active or paused workflow exists.
        """
        self._ensure_exists()
        if self._current is not None and self._current.status in {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.CANCELLED,
        }:
            raise RuntimeError(f"Cannot cancel workflow in '{self._current.status.value}' status")
        return self._transition(WorkflowStatus.CANCELLED, reason or "Cancelled")

    def get_current_context(self) -> dict[str, Any]:
        """Return the current workflow context as a dictionary.

        Returns:
            The workflow dict, or a status message if no workflow is active.
        """
        if self._current is None:
            return {
                "status": "idle",
                "message": "No active workflow. Use start_workflow() to begin.",
            }
        return self._current.to_dict()

    def _ensure_active(self) -> None:
        """Verify there is an active workflow.

        Raises:
            RuntimeError: If no active workflow exists.
        """
        if self._current is None:
            raise RuntimeError("No active workflow")
        if self._current.status != WorkflowStatus.ACTIVE:
            raise RuntimeError(
                f"Workflow '{self._current.workflow_id}' is not active "
                f"(status: {self._current.status.value})"
            )

    def _ensure_exists(self) -> None:
        """Verify a workflow exists (any state).

        Raises:
            RuntimeError: If no workflow exists at all.
        """
        if self._current is None:
            raise RuntimeError("No workflow exists")

    def _transition(self, new_status: WorkflowStatus, reason: str) -> WorkflowContext:
        """Apply a status transition to the current workflow.

        Args:
            new_status: The target status.
            reason: Reason for the transition.

        Returns:
            The updated workflow context.
        """
        assert self._current is not None  # noqa: S101
        old_status = self._current.status
        self._current.status = new_status
        self._current.history.append(
            {
                "from": old_status.value,
                "to": new_status.value,
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "reason": reason,
            }
        )
        logger.info(
            "Workflow '%s': %s → %s (%s)",
            self._current.workflow_id,
            old_status.value,
            new_status.value,
            reason,
        )
        return self._current
