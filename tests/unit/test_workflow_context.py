"""Tests for the WorkflowContextProvider module."""

from __future__ import annotations

import pytest

from atlas_mcp.context.workflow import (
    WorkflowContext,
    WorkflowContextProvider,
    WorkflowStatus,
    WorkflowType,
)

# ---------------------------------------------------------------------------
# WorkflowType / WorkflowStatus tests
# ---------------------------------------------------------------------------


class TestWorkflowType:
    """Tests for the WorkflowType enum."""

    def test_should_have_five_types(self) -> None:
        assert len(WorkflowType) == 5

    def test_should_contain_expected_values(self) -> None:
        expected = {"feature", "bug", "refactor", "docs", "infra"}
        assert {t.value for t in WorkflowType} == expected


class TestWorkflowStatus:
    """Tests for the WorkflowStatus enum."""

    def test_should_have_four_statuses(self) -> None:
        assert len(WorkflowStatus) == 4

    def test_should_contain_expected_values(self) -> None:
        expected = {"active", "paused", "completed", "cancelled"}
        assert {s.value for s in WorkflowStatus} == expected


# ---------------------------------------------------------------------------
# WorkflowContext tests
# ---------------------------------------------------------------------------


class TestWorkflowContext:
    """Tests for the WorkflowContext dataclass."""

    def test_should_create_with_defaults(self) -> None:
        ctx = WorkflowContext(
            workflow_id="P2-D6",
            workflow_type=WorkflowType.FEATURE,
            title="Test workflow",
        )
        assert ctx.status == WorkflowStatus.ACTIVE
        assert ctx.started_at != ""
        assert ctx.metadata == {}
        assert ctx.history == []

    def test_should_preserve_explicit_started_at(self) -> None:
        ctx = WorkflowContext(
            workflow_id="P2-D6",
            workflow_type=WorkflowType.BUG,
            title="Fix",
            started_at="2026-01-01T00:00:00+00:00",
        )
        assert ctx.started_at == "2026-01-01T00:00:00+00:00"

    def test_to_dict_should_return_all_fields(self) -> None:
        ctx = WorkflowContext(
            workflow_id="P2-D6",
            workflow_type=WorkflowType.FEATURE,
            title="Test",
            description="A description",
            branch="FET/P2-D6",
            metadata={"key": "value"},
        )
        d = ctx.to_dict()
        assert d["workflow_id"] == "P2-D6"
        assert d["workflow_type"] == "feature"
        assert d["title"] == "Test"
        assert d["description"] == "A description"
        assert d["status"] == "active"
        assert d["branch"] == "FET/P2-D6"
        assert d["metadata"] == {"key": "value"}
        assert isinstance(d["history"], list)

    def test_to_dict_should_serialize_workflow_type_as_string(self) -> None:
        ctx = WorkflowContext(
            workflow_id="X",
            workflow_type=WorkflowType.REFACTOR,
            title="Refactor",
        )
        assert ctx.to_dict()["workflow_type"] == "refactor"


# ---------------------------------------------------------------------------
# WorkflowContextProvider — start_workflow tests
# ---------------------------------------------------------------------------


class TestWorkflowContextProviderStart:
    """Tests for WorkflowContextProvider.start_workflow."""

    def test_should_start_new_workflow(self) -> None:
        provider = WorkflowContextProvider()
        wf = provider.start_workflow("P2-D6", WorkflowType.FEATURE, "New feature")
        assert wf.workflow_id == "P2-D6"
        assert wf.status == WorkflowStatus.ACTIVE
        assert provider.current is wf

    def test_should_record_start_in_history(self) -> None:
        provider = WorkflowContextProvider()
        wf = provider.start_workflow("P2-D6", WorkflowType.FEATURE, "New feature")
        assert len(wf.history) == 1
        assert wf.history[0]["status"] == "active"
        assert wf.history[0]["reason"] == "Workflow started"

    def test_should_auto_complete_previous_active_workflow(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D5", WorkflowType.FEATURE, "Previous")
        wf2 = provider.start_workflow("P2-D6", WorkflowType.FEATURE, "New")
        assert wf2.workflow_id == "P2-D6"
        assert provider.current is wf2

    def test_should_reject_empty_workflow_id(self) -> None:
        provider = WorkflowContextProvider()
        with pytest.raises(ValueError, match="workflow_id"):
            provider.start_workflow("", WorkflowType.FEATURE, "Title")

    def test_should_reject_blank_workflow_id(self) -> None:
        provider = WorkflowContextProvider()
        with pytest.raises(ValueError, match="workflow_id"):
            provider.start_workflow("   ", WorkflowType.FEATURE, "Title")

    def test_should_reject_empty_title(self) -> None:
        provider = WorkflowContextProvider()
        with pytest.raises(ValueError, match="title"):
            provider.start_workflow("P2-D6", WorkflowType.FEATURE, "")

    def test_should_accept_description_and_branch(self) -> None:
        provider = WorkflowContextProvider()
        wf = provider.start_workflow(
            "P2-D6",
            WorkflowType.BUG,
            "Fix bug",
            description="Details",
            branch="BUG/P2-D6",
        )
        assert wf.description == "Details"
        assert wf.branch == "BUG/P2-D6"

    def test_should_accept_metadata(self) -> None:
        provider = WorkflowContextProvider()
        wf = provider.start_workflow(
            "P2-D6",
            WorkflowType.INFRA,
            "Infra",
            metadata={"priority": "high"},
        )
        assert wf.metadata == {"priority": "high"}


# ---------------------------------------------------------------------------
# WorkflowContextProvider — pause / resume tests
# ---------------------------------------------------------------------------


class TestWorkflowContextProviderPauseResume:
    """Tests for pause_workflow and resume_workflow."""

    def test_should_pause_active_workflow(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        wf = provider.pause_workflow(reason="Lunch break")
        assert wf.status == WorkflowStatus.PAUSED
        assert len(wf.history) == 2

    def test_should_resume_paused_workflow(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        provider.pause_workflow()
        wf = provider.resume_workflow(reason="Back")
        assert wf.status == WorkflowStatus.ACTIVE
        assert len(wf.history) == 3

    def test_should_raise_when_pausing_without_workflow(self) -> None:
        provider = WorkflowContextProvider()
        with pytest.raises(RuntimeError, match="No active workflow"):
            provider.pause_workflow()

    def test_should_raise_when_resuming_without_workflow(self) -> None:
        provider = WorkflowContextProvider()
        with pytest.raises(RuntimeError, match="No workflow to resume"):
            provider.resume_workflow()

    def test_should_raise_when_resuming_active_workflow(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        with pytest.raises(RuntimeError, match="Cannot resume"):
            provider.resume_workflow()

    def test_should_raise_when_pausing_completed_workflow(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        provider.complete_workflow()
        with pytest.raises(RuntimeError, match="not active"):
            provider.pause_workflow()

    def test_pause_should_use_default_reason(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        wf = provider.pause_workflow()
        assert wf.history[-1]["reason"] == "Paused"

    def test_resume_should_use_default_reason(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        provider.pause_workflow()
        wf = provider.resume_workflow()
        assert wf.history[-1]["reason"] == "Resumed"


# ---------------------------------------------------------------------------
# WorkflowContextProvider — complete / cancel tests
# ---------------------------------------------------------------------------


class TestWorkflowContextProviderCompleteCancel:
    """Tests for complete_workflow and cancel_workflow."""

    def test_should_complete_active_workflow(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        wf = provider.complete_workflow(reason="Done")
        assert wf.status == WorkflowStatus.COMPLETED

    def test_should_complete_paused_workflow(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        provider.pause_workflow()
        wf = provider.complete_workflow()
        assert wf.status == WorkflowStatus.COMPLETED

    def test_should_cancel_active_workflow(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        wf = provider.cancel_workflow(reason="Scope changed")
        assert wf.status == WorkflowStatus.CANCELLED

    def test_should_cancel_paused_workflow(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        provider.pause_workflow()
        wf = provider.cancel_workflow()
        assert wf.status == WorkflowStatus.CANCELLED

    def test_should_raise_when_completing_already_completed(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        provider.complete_workflow()
        with pytest.raises(RuntimeError, match="Cannot complete"):
            provider.complete_workflow()

    def test_should_raise_when_cancelling_already_cancelled(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        provider.cancel_workflow()
        with pytest.raises(RuntimeError, match="Cannot cancel"):
            provider.cancel_workflow()

    def test_should_raise_when_completing_no_workflow(self) -> None:
        provider = WorkflowContextProvider()
        with pytest.raises(RuntimeError, match="No workflow exists"):
            provider.complete_workflow()

    def test_should_raise_when_cancelling_no_workflow(self) -> None:
        provider = WorkflowContextProvider()
        with pytest.raises(RuntimeError, match="No workflow exists"):
            provider.cancel_workflow()

    def test_complete_should_use_default_reason(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        wf = provider.complete_workflow()
        assert wf.history[-1]["reason"] == "Completed"

    def test_cancel_should_use_default_reason(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        wf = provider.cancel_workflow()
        assert wf.history[-1]["reason"] == "Cancelled"


# ---------------------------------------------------------------------------
# WorkflowContextProvider — get_current_context tests
# ---------------------------------------------------------------------------


class TestWorkflowContextProviderGetContext:
    """Tests for get_current_context."""

    def test_should_return_idle_when_no_workflow(self) -> None:
        provider = WorkflowContextProvider()
        ctx = provider.get_current_context()
        assert ctx["status"] == "idle"
        assert "message" in ctx

    def test_should_return_workflow_dict_when_active(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        ctx = provider.get_current_context()
        assert ctx["workflow_id"] == "P2-D6"
        assert ctx["status"] == "active"
        assert ctx["workflow_type"] == "feature"

    def test_should_return_paused_status(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        provider.pause_workflow()
        ctx = provider.get_current_context()
        assert ctx["status"] == "paused"

    def test_should_include_history(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        provider.pause_workflow()
        provider.resume_workflow()
        ctx = provider.get_current_context()
        assert len(ctx["history"]) == 3


# ---------------------------------------------------------------------------
# History tracking tests
# ---------------------------------------------------------------------------


class TestWorkflowHistory:
    """Tests for workflow history tracking."""

    def test_history_should_track_from_and_to(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        provider.pause_workflow(reason="Break")
        wf = provider.current
        assert wf is not None
        last_entry = wf.history[-1]
        assert last_entry["from"] == "active"
        assert last_entry["to"] == "paused"
        assert last_entry["reason"] == "Break"
        assert "timestamp" in last_entry

    def test_full_lifecycle_history(self) -> None:
        provider = WorkflowContextProvider()
        provider.start_workflow("P2-D6", WorkflowType.FEATURE, "Feature")
        provider.pause_workflow()
        provider.resume_workflow()
        provider.complete_workflow()
        wf = provider.current
        assert wf is not None
        assert len(wf.history) == 4
        statuses = [h.get("to", h.get("status")) for h in wf.history]
        assert statuses == ["active", "paused", "active", "completed"]
