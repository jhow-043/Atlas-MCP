"""Tests for hardening validation across all MCP tools.

Covers edge cases: empty/whitespace strings, values exceeding maximum
lengths, out-of-range numbers, boundary values, and error message
content. Ensures no malformed input causes a crash.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.server.fastmcp.exceptions import ToolError
from mcp.shared.message import SessionMessage

from atlas_mcp.server import create_server
from atlas_mcp.tools.executor import ToolExecutor
from atlas_mcp.tools.register_adr import (
    _MAX_FIELD_LENGTH as ADR_MAX_FIELD_LENGTH,
)
from atlas_mcp.tools.register_adr import (
    _MAX_TITLE_LENGTH as ADR_MAX_TITLE_LENGTH,
)
from atlas_mcp.tools.register_adr import (
    _validate_adr_params,
    register_register_adr,
)
from atlas_mcp.tools.search_context import (
    _MAX_LIMIT,
    _MAX_QUERY_LENGTH,
    _validate_search_params,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _run_tool_test(callback: Any) -> None:
    """Set up an in-memory MCP session with tools and call *callback*."""
    server = create_server()
    ToolExecutor.register(server)

    send_c2s, recv_c2s = anyio.create_memory_object_stream[SessionMessage](1)
    send_s2c, recv_s2c = anyio.create_memory_object_stream[SessionMessage](1)

    init_options = server._mcp_server.create_initialization_options()

    async with anyio.create_task_group() as tg:
        tg.start_soon(
            server._mcp_server.run,
            recv_c2s,
            send_s2c,
            init_options,
            True,
        )
        async with ClientSession(recv_s2c, send_c2s) as session:
            await session.initialize()
            await callback(session)
            tg.cancel_scope.cancel()


def _assert_error_contains(result: Any, *fragments: str) -> None:
    """Assert that the tool result is an error containing all fragments."""
    assert result.isError is True
    text = result.content[0].text  # type: ignore[union-attr]
    for fragment in fragments:
        assert fragment in text, f"Expected {fragment!r} in error: {text}"


def _capture_register_adr_fn() -> Any:
    """Register register_adr on a mock server and return the inner function."""
    captured_fn = None

    def capture_tool(**kwargs: object) -> object:
        def decorator(fn: object) -> object:
            nonlocal captured_fn
            captured_fn = fn
            return fn

        return decorator

    mock_server = MagicMock()
    mock_server.tool = capture_tool
    register_register_adr(mock_server)

    assert captured_fn is not None
    return captured_fn


# ---------------------------------------------------------------------------
# TestSearchContextValidation
# ---------------------------------------------------------------------------


class TestSearchContextValidation:
    """Tests for search_context parameter validation edge cases."""

    # -- query ---------------------------------------------------------------

    def test_should_reject_empty_query(self) -> None:
        """Validate that empty string is rejected."""
        with pytest.raises(ToolError, match="query"):
            _validate_search_params("", 5, 0.7)

    def test_should_reject_whitespace_only_query(self) -> None:
        """Validate that whitespace-only query is rejected."""
        with pytest.raises(ToolError, match="query"):
            _validate_search_params("   \t\n  ", 5, 0.7)

    def test_should_reject_query_exceeding_max_length(self) -> None:
        """Validate that query longer than _MAX_QUERY_LENGTH is rejected."""
        long_query = "a" * (_MAX_QUERY_LENGTH + 1)
        with pytest.raises(ToolError, match="max"):
            _validate_search_params(long_query, 5, 0.7)

    def test_should_accept_query_at_max_length(self) -> None:
        """Validate that query exactly at _MAX_QUERY_LENGTH is accepted."""
        exact_query = "a" * _MAX_QUERY_LENGTH
        _validate_search_params(exact_query, 5, 0.7)

    # -- limit ---------------------------------------------------------------

    def test_should_reject_zero_limit(self) -> None:
        """Validate that limit=0 is rejected."""
        with pytest.raises(ToolError, match="limit"):
            _validate_search_params("test", 0, 0.7)

    def test_should_reject_negative_limit(self) -> None:
        """Validate that negative limit is rejected."""
        with pytest.raises(ToolError, match="limit"):
            _validate_search_params("test", -10, 0.7)

    def test_should_accept_limit_one(self) -> None:
        """Validate that limit=1 (minimum) is accepted."""
        _validate_search_params("test", 1, 0.7)

    def test_should_accept_limit_at_max(self) -> None:
        """Validate that limit=_MAX_LIMIT is accepted."""
        _validate_search_params("test", _MAX_LIMIT, 0.7)

    def test_should_reject_limit_above_max(self) -> None:
        """Validate that limit > _MAX_LIMIT is rejected."""
        with pytest.raises(ToolError, match="limit"):
            _validate_search_params("test", _MAX_LIMIT + 1, 0.7)

    # -- similarity_threshold ------------------------------------------------

    def test_should_accept_threshold_zero(self) -> None:
        """Validate that threshold=0.0 is accepted (boundary)."""
        _validate_search_params("test", 5, 0.0)

    def test_should_accept_threshold_one(self) -> None:
        """Validate that threshold=1.0 is accepted (boundary)."""
        _validate_search_params("test", 5, 1.0)

    def test_should_reject_threshold_slightly_above_one(self) -> None:
        """Validate that threshold=1.01 is rejected."""
        with pytest.raises(ToolError, match="similarity_threshold"):
            _validate_search_params("test", 5, 1.01)

    def test_should_reject_threshold_slightly_below_zero(self) -> None:
        """Validate that threshold=-0.01 is rejected."""
        with pytest.raises(ToolError, match="similarity_threshold"):
            _validate_search_params("test", 5, -0.01)

    def test_should_reject_large_positive_threshold(self) -> None:
        """Validate that threshold=100.0 is rejected."""
        with pytest.raises(ToolError, match="similarity_threshold"):
            _validate_search_params("test", 5, 100.0)

    def test_should_reject_large_negative_threshold(self) -> None:
        """Validate that threshold=-100.0 is rejected."""
        with pytest.raises(ToolError, match="similarity_threshold"):
            _validate_search_params("test", 5, -100.0)

    # -- error message content -----------------------------------------------

    def test_empty_query_error_should_contain_parameter_name(self) -> None:
        """Validate that error message mentions 'query'."""
        with pytest.raises(ToolError) as exc_info:
            _validate_search_params("", 5, 0.7)
        error_text = str(exc_info.value)
        assert "INVALID_PARAMETER" in error_text
        assert "query" in error_text

    def test_limit_error_should_contain_parameter_name(self) -> None:
        """Validate that error message mentions 'limit'."""
        with pytest.raises(ToolError) as exc_info:
            _validate_search_params("test", -1, 0.7)
        error_text = str(exc_info.value)
        assert "INVALID_PARAMETER" in error_text
        assert "limit" in error_text

    def test_threshold_error_should_contain_parameter_name(self) -> None:
        """Validate that error message mentions 'similarity_threshold'."""
        with pytest.raises(ToolError) as exc_info:
            _validate_search_params("test", 5, 2.0)
        error_text = str(exc_info.value)
        assert "INVALID_PARAMETER" in error_text
        assert "similarity_threshold" in error_text

    # -- combined valid params -----------------------------------------------

    def test_should_accept_typical_valid_params(self) -> None:
        """Validate that typical valid parameters pass."""
        _validate_search_params("architecture overview", 10, 0.5)

    def test_should_accept_single_char_query(self) -> None:
        """Validate that a single char query is accepted."""
        _validate_search_params("a", 1, 0.0)


# ---------------------------------------------------------------------------
# TestSearchContextViaMCP
# ---------------------------------------------------------------------------


class TestSearchContextViaMCP:
    """Tests for search_context validation via MCP protocol."""

    async def test_should_return_error_for_empty_query(self) -> None:
        """Validate MCP returns isError=True for empty query."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "search_context",
                {"query": ""},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "query")

        await _run_tool_test(_assert)

    async def test_should_return_error_for_whitespace_query(self) -> None:
        """Validate MCP returns isError=True for whitespace-only query."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "search_context",
                {"query": "   "},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "query")

        await _run_tool_test(_assert)

    async def test_should_return_error_for_limit_zero(self) -> None:
        """Validate MCP returns isError=True for limit=0."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "search_context",
                {"query": "test", "limit": 0},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "limit")

        await _run_tool_test(_assert)

    async def test_should_return_error_for_negative_limit(self) -> None:
        """Validate MCP returns isError=True for negative limit."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "search_context",
                {"query": "test", "limit": -5},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "limit")

        await _run_tool_test(_assert)

    async def test_should_return_error_for_limit_above_max(self) -> None:
        """Validate MCP returns isError=True for limit > _MAX_LIMIT."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "search_context",
                {"query": "test", "limit": _MAX_LIMIT + 1},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "limit")

        await _run_tool_test(_assert)

    async def test_should_return_error_for_invalid_threshold(self) -> None:
        """Validate MCP returns isError=True for threshold > 1."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "search_context",
                {"query": "test", "similarity_threshold": 1.5},
            )
            _assert_error_contains(
                result, "INVALID_PARAMETER", "similarity_threshold"
            )

        await _run_tool_test(_assert)

    async def test_should_return_error_for_negative_threshold(self) -> None:
        """Validate MCP returns isError=True for threshold < 0."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "search_context",
                {"query": "test", "similarity_threshold": -0.5},
            )
            _assert_error_contains(
                result, "INVALID_PARAMETER", "similarity_threshold"
            )

        await _run_tool_test(_assert)


# ---------------------------------------------------------------------------
# TestPlanFeatureValidation
# ---------------------------------------------------------------------------


class TestPlanFeatureValidation:
    """Tests for plan_feature validation edge cases via MCP protocol."""

    async def test_should_reject_empty_title(self) -> None:
        """Validate that empty title is rejected."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "plan_feature",
                {"title": "", "description": "Some description"},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "title")

        await _run_tool_test(_assert)

    async def test_should_reject_whitespace_title(self) -> None:
        """Validate that whitespace-only title is rejected."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "plan_feature",
                {"title": "   \t  ", "description": "Valid desc"},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "title")

        await _run_tool_test(_assert)

    async def test_should_reject_empty_description(self) -> None:
        """Validate that empty description is rejected."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "plan_feature",
                {"title": "Feature X", "description": ""},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "description")

        await _run_tool_test(_assert)

    async def test_should_reject_whitespace_description(self) -> None:
        """Validate that whitespace-only description is rejected."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "plan_feature",
                {"title": "Feature X", "description": "  \n  "},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "description")

        await _run_tool_test(_assert)

    async def test_should_reject_title_exceeding_max_length(self) -> None:
        """Validate that title longer than 200 chars is rejected."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "plan_feature",
                {"title": "A" * 201, "description": "desc"},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "title", "max")

        await _run_tool_test(_assert)

    async def test_should_accept_title_at_max_length(self) -> None:
        """Validate that title exactly at 200 chars is accepted."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "plan_feature",
                {"title": "A" * 200, "description": "Valid desc"},
            )
            assert result.isError is not True

        await _run_tool_test(_assert)

    async def test_should_reject_description_exceeding_max_length(self) -> None:
        """Validate that description longer than 10000 chars is rejected."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "plan_feature",
                {"title": "Feature", "description": "D" * 10_001},
            )
            _assert_error_contains(
                result, "INVALID_PARAMETER", "description", "max"
            )

        await _run_tool_test(_assert)

    async def test_should_accept_description_at_max_length(self) -> None:
        """Validate that description exactly at 10000 chars is accepted."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "plan_feature",
                {"title": "Feature", "description": "D" * 10_000},
            )
            assert result.isError is not True

        await _run_tool_test(_assert)

    async def test_should_accept_empty_optional_fields(self) -> None:
        """Validate that empty requirements and constraints are accepted."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "plan_feature",
                {
                    "title": "F",
                    "description": "D",
                    "requirements": "",
                    "constraints": "",
                },
            )
            assert result.isError is not True

        await _run_tool_test(_assert)

    async def test_error_message_should_contain_error_info(self) -> None:
        """Validate that error content contains structured error info."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "plan_feature",
                {"title": "", "description": "desc"},
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "INVALID_PARAMETER" in text
            assert "title" in text

        await _run_tool_test(_assert)


# ---------------------------------------------------------------------------
# TestAnalyzeBugValidation
# ---------------------------------------------------------------------------


class TestAnalyzeBugValidation:
    """Tests for analyze_bug validation edge cases via MCP protocol."""

    async def test_should_reject_empty_title(self) -> None:
        """Validate that empty title is rejected."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "analyze_bug",
                {"title": "", "description": "Something broke"},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "title")

        await _run_tool_test(_assert)

    async def test_should_reject_whitespace_title(self) -> None:
        """Validate that whitespace-only title is rejected."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "analyze_bug",
                {"title": "\t\n  ", "description": "desc"},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "title")

        await _run_tool_test(_assert)

    async def test_should_reject_empty_description(self) -> None:
        """Validate that empty description is rejected."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "analyze_bug",
                {"title": "Bug X", "description": ""},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "description")

        await _run_tool_test(_assert)

    async def test_should_reject_whitespace_description(self) -> None:
        """Validate that whitespace-only description is rejected."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "analyze_bug",
                {"title": "Bug X", "description": "   "},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "description")

        await _run_tool_test(_assert)

    async def test_should_reject_title_exceeding_max_length(self) -> None:
        """Validate that title longer than 200 chars is rejected."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "analyze_bug",
                {"title": "B" * 201, "description": "desc"},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "title", "max")

        await _run_tool_test(_assert)

    async def test_should_accept_title_at_max_length(self) -> None:
        """Validate that title exactly at 200 chars is accepted."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "analyze_bug",
                {"title": "B" * 200, "description": "Valid desc"},
            )
            assert result.isError is not True

        await _run_tool_test(_assert)

    async def test_should_reject_description_exceeding_max_length(self) -> None:
        """Validate that description longer than 10000 chars is rejected."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "analyze_bug",
                {"title": "Bug", "description": "X" * 10_001},
            )
            _assert_error_contains(
                result, "INVALID_PARAMETER", "description", "max"
            )

        await _run_tool_test(_assert)

    async def test_should_accept_description_at_max_length(self) -> None:
        """Validate that description exactly at 10000 chars is accepted."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "analyze_bug",
                {"title": "Bug", "description": "X" * 10_000},
            )
            assert result.isError is not True

        await _run_tool_test(_assert)

    async def test_should_accept_empty_optional_fields(self) -> None:
        """Validate that empty optional fields are accepted."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "analyze_bug",
                {
                    "title": "Bug",
                    "description": "Desc",
                    "expected_behavior": "",
                    "steps_to_reproduce": "",
                },
            )
            assert result.isError is not True

        await _run_tool_test(_assert)

    async def test_error_message_should_contain_error_info(self) -> None:
        """Validate that error content contains structured error info."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "analyze_bug",
                {"title": "", "description": "desc"},
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "INVALID_PARAMETER" in text
            assert "title" in text

        await _run_tool_test(_assert)


# ---------------------------------------------------------------------------
# TestRegisterAdrValidation
# ---------------------------------------------------------------------------


class TestRegisterAdrValidation:
    """Tests for register_adr _validate_adr_params edge cases."""

    # -- title ---------------------------------------------------------------

    def test_should_reject_empty_title(self) -> None:
        """Validate that empty title is rejected."""
        with pytest.raises(ToolError, match="title"):
            _validate_adr_params("", "ctx", "dec", "cons")

    def test_should_reject_whitespace_title(self) -> None:
        """Validate that whitespace-only title is rejected."""
        with pytest.raises(ToolError, match="title"):
            _validate_adr_params("  \t\n  ", "ctx", "dec", "cons")

    def test_should_reject_title_exceeding_max_length(self) -> None:
        """Validate that title > 200 chars is rejected."""
        with pytest.raises(ToolError, match="title"):
            _validate_adr_params("T" * (ADR_MAX_TITLE_LENGTH + 1), "ctx", "dec", "cons")

    def test_should_accept_title_at_max_length(self) -> None:
        """Validate that title at exactly 200 chars is accepted."""
        _validate_adr_params("T" * ADR_MAX_TITLE_LENGTH, "ctx", "dec", "cons")

    # -- context -------------------------------------------------------------

    def test_should_reject_empty_context(self) -> None:
        """Validate that empty context is rejected."""
        with pytest.raises(ToolError, match="context"):
            _validate_adr_params("title", "", "dec", "cons")

    def test_should_reject_whitespace_context(self) -> None:
        """Validate that whitespace-only context is rejected."""
        with pytest.raises(ToolError, match="context"):
            _validate_adr_params("title", "   ", "dec", "cons")

    def test_should_reject_context_exceeding_max_length(self) -> None:
        """Validate that context > 10000 chars is rejected."""
        with pytest.raises(ToolError, match="context"):
            _validate_adr_params("title", "C" * (ADR_MAX_FIELD_LENGTH + 1), "dec", "cons")

    def test_should_accept_context_at_max_length(self) -> None:
        """Validate that context at exactly 10000 chars is accepted."""
        _validate_adr_params("title", "C" * ADR_MAX_FIELD_LENGTH, "dec", "cons")

    # -- decision ------------------------------------------------------------

    def test_should_reject_empty_decision(self) -> None:
        """Validate that empty decision is rejected."""
        with pytest.raises(ToolError, match="decision"):
            _validate_adr_params("title", "ctx", "", "cons")

    def test_should_reject_whitespace_decision(self) -> None:
        """Validate that whitespace-only decision is rejected."""
        with pytest.raises(ToolError, match="decision"):
            _validate_adr_params("title", "ctx", "   ", "cons")

    def test_should_reject_decision_exceeding_max_length(self) -> None:
        """Validate that decision > 10000 chars is rejected."""
        with pytest.raises(ToolError, match="decision"):
            _validate_adr_params("title", "ctx", "D" * (ADR_MAX_FIELD_LENGTH + 1), "cons")

    def test_should_accept_decision_at_max_length(self) -> None:
        """Validate that decision at exactly 10000 chars is accepted."""
        _validate_adr_params("title", "ctx", "D" * ADR_MAX_FIELD_LENGTH, "cons")

    # -- consequences --------------------------------------------------------

    def test_should_reject_empty_consequences(self) -> None:
        """Validate that empty consequences is rejected."""
        with pytest.raises(ToolError, match="consequences"):
            _validate_adr_params("title", "ctx", "dec", "")

    def test_should_reject_whitespace_consequences(self) -> None:
        """Validate that whitespace-only consequences is rejected."""
        with pytest.raises(ToolError, match="consequences"):
            _validate_adr_params("title", "ctx", "dec", "   ")

    def test_should_reject_consequences_exceeding_max_length(self) -> None:
        """Validate that consequences > 10000 chars is rejected."""
        with pytest.raises(ToolError, match="consequences"):
            _validate_adr_params("title", "ctx", "dec", "E" * (ADR_MAX_FIELD_LENGTH + 1))

    def test_should_accept_consequences_at_max_length(self) -> None:
        """Validate that consequences at exactly 10000 chars is accepted."""
        _validate_adr_params("title", "ctx", "dec", "E" * ADR_MAX_FIELD_LENGTH)

    # -- error message content -----------------------------------------------

    def test_error_should_contain_invalid_parameter_code(self) -> None:
        """Validate that error JSON contains INVALID_PARAMETER."""
        with pytest.raises(ToolError) as exc_info:
            _validate_adr_params("", "ctx", "dec", "cons")
        error_text = str(exc_info.value)
        assert "INVALID_PARAMETER" in error_text
        assert "title" in error_text

    def test_max_length_error_should_mention_limit(self) -> None:
        """Validate that max length error mentions the limit value."""
        with pytest.raises(ToolError) as exc_info:
            _validate_adr_params("T" * (ADR_MAX_TITLE_LENGTH + 1), "c", "d", "e")
        error_text = str(exc_info.value)
        assert str(ADR_MAX_TITLE_LENGTH) in error_text

    # -- combined valid params -----------------------------------------------

    def test_should_accept_all_valid_params(self) -> None:
        """Validate that typical valid params pass."""
        _validate_adr_params("Use asyncpg", "Need async DB", "Use asyncpg", "Fast")

    def test_should_accept_minimal_valid_params(self) -> None:
        """Validate that single-char params are accepted."""
        _validate_adr_params("T", "C", "D", "E")


# ---------------------------------------------------------------------------
# TestRegisterAdrViaMCP
# ---------------------------------------------------------------------------


class TestRegisterAdrViaMCP:
    """Tests for register_adr validation via the registered tool function."""

    @patch("atlas_mcp.tools.register_adr._discover_adr_dir")
    def test_should_reject_empty_title_via_tool(
        self, mock_discover: MagicMock, tmp_path: Path
    ) -> None:
        """Validate that calling the tool with empty title raises ToolError."""
        mock_discover.return_value = tmp_path
        fn = _capture_register_adr_fn()
        with pytest.raises(ToolError):
            fn(title="", context="C", decision="D", consequences="E")

    @patch("atlas_mcp.tools.register_adr._discover_adr_dir")
    def test_should_reject_whitespace_title_via_tool(
        self, mock_discover: MagicMock, tmp_path: Path
    ) -> None:
        """Validate that calling the tool with whitespace title raises ToolError."""
        mock_discover.return_value = tmp_path
        fn = _capture_register_adr_fn()
        with pytest.raises(ToolError):
            fn(title="   ", context="C", decision="D", consequences="E")

    @patch("atlas_mcp.tools.register_adr._discover_adr_dir")
    def test_should_reject_long_title_via_tool(
        self, mock_discover: MagicMock, tmp_path: Path
    ) -> None:
        """Validate that title exceeding max length raises ToolError."""
        mock_discover.return_value = tmp_path
        fn = _capture_register_adr_fn()
        with pytest.raises(ToolError):
            fn(
                title="T" * (ADR_MAX_TITLE_LENGTH + 1),
                context="C",
                decision="D",
                consequences="E",
            )

    @patch("atlas_mcp.tools.register_adr._discover_adr_dir")
    def test_should_reject_whitespace_context_via_tool(
        self, mock_discover: MagicMock, tmp_path: Path
    ) -> None:
        """Validate that whitespace-only context raises ToolError."""
        mock_discover.return_value = tmp_path
        fn = _capture_register_adr_fn()
        with pytest.raises(ToolError):
            fn(title="T", context="  \n  ", decision="D", consequences="E")

    @patch("atlas_mcp.tools.register_adr._discover_adr_dir")
    def test_should_reject_whitespace_decision_via_tool(
        self, mock_discover: MagicMock, tmp_path: Path
    ) -> None:
        """Validate that whitespace-only decision raises ToolError."""
        mock_discover.return_value = tmp_path
        fn = _capture_register_adr_fn()
        with pytest.raises(ToolError):
            fn(title="T", context="C", decision="  ", consequences="E")

    @patch("atlas_mcp.tools.register_adr._discover_adr_dir")
    def test_should_reject_whitespace_consequences_via_tool(
        self, mock_discover: MagicMock, tmp_path: Path
    ) -> None:
        """Validate that whitespace-only consequences raises ToolError."""
        mock_discover.return_value = tmp_path
        fn = _capture_register_adr_fn()
        with pytest.raises(ToolError):
            fn(title="T", context="C", decision="D", consequences="\t")


# ---------------------------------------------------------------------------
# TestNoCrashOnMalformedInput
# ---------------------------------------------------------------------------


class TestNoCrashOnMalformedInput:
    """Ensure that no malformed input causes an unhandled crash.

    These tests verify that all tools handle edge cases gracefully
    and return structured errors instead of crashing.
    """

    async def test_search_context_with_unicode_query(self) -> None:
        """Validate that unicode query does not crash."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "search_context",
                {"query": "búsqueda con émojis 🔍 e açúcar"},
            )
            # Should either succeed or return a structured error, not crash
            # (without configured RAG, returns SERVICE_UNAVAILABLE)
            assert result.content is not None
            assert len(result.content) > 0

        await _run_tool_test(_assert)

    async def test_plan_feature_with_newlines_in_title(self) -> None:
        """Validate that newlines in title do not crash."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "plan_feature",
                {"title": "Feature\nwith\nnewlines", "description": "desc"},
            )
            # Should succeed (newlines are valid chars)
            assert result.isError is not True

        await _run_tool_test(_assert)

    async def test_analyze_bug_with_special_chars(self) -> None:
        """Validate that special characters do not crash."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "analyze_bug",
                {
                    "title": "<script>alert('xss')</script>",
                    "description": "SQL: '; DROP TABLE users;--",
                },
            )
            # Should succeed (we don't sanitize, just validate emptiness/length)
            assert result.isError is not True

        await _run_tool_test(_assert)

    async def test_plan_feature_with_only_spaces_in_requirements(self) -> None:
        """Validate that whitespace-only requirements don't crash."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "plan_feature",
                {
                    "title": "F",
                    "description": "D",
                    "requirements": "   \n   \n   ",
                },
            )
            assert result.isError is not True
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            # Whitespace-only lines should be filtered out
            assert data["feature"]["requirements"] == []

        await _run_tool_test(_assert)

    async def test_analyze_bug_with_only_spaces_in_steps(self) -> None:
        """Validate that whitespace-only steps don't crash."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "analyze_bug",
                {
                    "title": "B",
                    "description": "D",
                    "steps_to_reproduce": "\n\n\n",
                },
            )
            assert result.isError is not True
            data = json.loads(result.content[0].text)  # type: ignore[union-attr]
            assert data["bug"]["steps_to_reproduce"] == []

        await _run_tool_test(_assert)

    def test_register_adr_validate_does_not_crash_on_long_unicode(self) -> None:
        """Validate that very long unicode strings don't cause crashes."""
        long_unicode = "ñ" * (ADR_MAX_FIELD_LENGTH + 1)
        with pytest.raises(ToolError):
            _validate_adr_params("title", long_unicode, "dec", "cons")

    async def test_search_context_with_json_in_query(self) -> None:
        """Validate that JSON-like query strings don't crash."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "search_context",
                {"query": '{"key": "value", "nested": {"a": 1}}'},
            )
            # Should either succeed or return structured error, not crash
            assert result.content is not None
            assert len(result.content) > 0

        await _run_tool_test(_assert)

    async def test_search_context_with_long_query_returns_error(self) -> None:
        """Validate that extremely long query returns error, not crash."""

        async def _assert(session: ClientSession) -> None:
            result = await session.call_tool(
                "search_context",
                {"query": "x" * (_MAX_QUERY_LENGTH + 1)},
            )
            _assert_error_contains(result, "INVALID_PARAMETER", "query", "max")

        await _run_tool_test(_assert)
