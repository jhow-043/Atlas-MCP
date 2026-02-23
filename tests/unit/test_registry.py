"""Tests for the ResourceRegistry and core resources."""

from __future__ import annotations

import json
from typing import Any

import anyio
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage

from atlas_mcp.resources.core_stack import (
    _CORE_STACK_DESCRIPTION,
    _CORE_STACK_NAME,
    _CORE_STACK_URI,
    register_core_stack,
)
from atlas_mcp.resources.registry import ResourceRegistry
from atlas_mcp.server import create_server

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _run_resource_test(callback: Any) -> None:
    """Set up an in-memory MCP session with resources and call *callback*.

    The server has ``ResourceRegistry.register()`` already applied so
    that ``resources/list`` and ``resources/read`` return real data.
    """
    server = create_server()
    ResourceRegistry.register(server)

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


# ---------------------------------------------------------------------------
# TestResourceRegistry
# ---------------------------------------------------------------------------


class TestResourceRegistry:
    """Tests for the ResourceRegistry class."""

    def test_should_register_resources_on_server(self) -> None:
        """Validate that register() adds resources to the server."""
        server = create_server()
        ResourceRegistry.register(server)

        resources = server._resource_manager.list_resources()
        assert len(resources) >= 3

    def test_should_register_core_stack_resource(self) -> None:
        """Validate that context://core/stack appears after registration."""
        server = create_server()
        ResourceRegistry.register(server)

        resources = server._resource_manager.list_resources()
        uris = [str(r.uri) for r in resources]
        assert _CORE_STACK_URI in uris

    def test_should_allow_direct_core_stack_registration(self) -> None:
        """Validate that register_core_stack can be called directly."""
        server = create_server()
        register_core_stack(server)

        resources = server._resource_manager.list_resources()
        uris = [str(r.uri) for r in resources]
        assert _CORE_STACK_URI in uris


# ---------------------------------------------------------------------------
# TestCoreStackResource
# ---------------------------------------------------------------------------


class TestCoreStackResource:
    """Tests for the context://core/stack resource content."""

    async def test_should_return_valid_json(self) -> None:
        """Validate that the resource returns valid JSON."""

        async def _assert(session: ClientSession) -> None:
            result = await session.read_resource(_CORE_STACK_URI)
            assert len(result.contents) == 1
            content = result.contents[0]
            data = json.loads(content.text)  # type: ignore[union-attr]
            assert isinstance(data, dict)

        await _run_resource_test(_assert)

    async def test_should_contain_project_name(self) -> None:
        """Validate that the JSON contains the project name."""

        async def _assert(session: ClientSession) -> None:
            result = await session.read_resource(_CORE_STACK_URI)
            data = json.loads(result.contents[0].text)  # type: ignore[union-attr]
            assert data["project"] == "atlas-mcp"

        await _run_resource_test(_assert)

    async def test_should_contain_language_info(self) -> None:
        """Validate that the JSON contains language information."""

        async def _assert(session: ClientSession) -> None:
            result = await session.read_resource(_CORE_STACK_URI)
            data = json.loads(result.contents[0].text)  # type: ignore[union-attr]
            assert data["language"]["name"] == "Python"
            assert data["language"]["version"] == ">=3.12"

        await _run_resource_test(_assert)

    async def test_should_contain_database_info(self) -> None:
        """Validate that the JSON contains dependency info."""

        async def _assert(session: ClientSession) -> None:
            result = await session.read_resource(_CORE_STACK_URI)
            data = json.loads(result.contents[0].text)  # type: ignore[union-attr]
            assert isinstance(data["dependencies"], list)
            assert any("asyncpg" in d for d in data["dependencies"])

        await _run_resource_test(_assert)

    async def test_should_match_stack_data_constant(self) -> None:
        """Validate that the resource returns expected keys."""

        async def _assert(session: ClientSession) -> None:
            result = await session.read_resource(_CORE_STACK_URI)
            data = json.loads(result.contents[0].text)  # type: ignore[union-attr]
            expected_keys = {
                "project",
                "version",
                "language",
                "runtime",
                "package_manager",
                "dependencies",
                "dev_dependencies",
                "linting",
                "type_checking",
                "ci",
            }
            assert expected_keys.issubset(data.keys())

        await _run_resource_test(_assert)

    async def test_should_have_correct_uri_in_list(self) -> None:
        """Validate that resources/list contains context://core/stack."""

        async def _assert(session: ClientSession) -> None:
            result = await session.list_resources()
            uris = [str(r.uri) for r in result.resources]
            assert _CORE_STACK_URI in uris

        await _run_resource_test(_assert)

    async def test_should_have_correct_name_in_list(self) -> None:
        """Validate that the resource name is correct in resources/list."""

        async def _assert(session: ClientSession) -> None:
            result = await session.list_resources()
            resource = next(r for r in result.resources if str(r.uri) == _CORE_STACK_URI)
            assert resource.name == _CORE_STACK_NAME

        await _run_resource_test(_assert)

    async def test_should_have_correct_description_in_list(self) -> None:
        """Validate that the resource description is correct."""

        async def _assert(session: ClientSession) -> None:
            result = await session.list_resources()
            resource = next(r for r in result.resources if str(r.uri) == _CORE_STACK_URI)
            assert resource.description == _CORE_STACK_DESCRIPTION

        await _run_resource_test(_assert)

    async def test_should_have_json_mime_type(self) -> None:
        """Validate that the resource MIME type is application/json."""

        async def _assert(session: ClientSession) -> None:
            result = await session.list_resources()
            resource = next(r for r in result.resources if str(r.uri) == _CORE_STACK_URI)
            assert resource.mimeType == "application/json"

        await _run_resource_test(_assert)

    async def test_should_contain_runtime_info(self) -> None:
        """Validate that the JSON contains runtime information."""

        async def _assert(session: ClientSession) -> None:
            result = await session.read_resource(_CORE_STACK_URI)
            data = json.loads(result.contents[0].text)  # type: ignore[union-attr]
            assert data["runtime"] == "Asyncio"

        await _run_resource_test(_assert)

    async def test_should_contain_sdk_info(self) -> None:
        """Validate that the JSON contains dependency list with mcp."""

        async def _assert(session: ClientSession) -> None:
            result = await session.read_resource(_CORE_STACK_URI)
            data = json.loads(result.contents[0].text)  # type: ignore[union-attr]
            assert any("mcp" in d for d in data["dependencies"])

        await _run_resource_test(_assert)

    async def test_should_contain_package_manager(self) -> None:
        """Validate that the JSON contains the package manager."""

        async def _assert(session: ClientSession) -> None:
            result = await session.read_resource(_CORE_STACK_URI)
            data = json.loads(result.contents[0].text)  # type: ignore[union-attr]
            assert data["package_manager"] == "uv"

        await _run_resource_test(_assert)

    async def test_should_contain_testing_tools(self) -> None:
        """Validate that the JSON contains dev dependency list."""

        async def _assert(session: ClientSession) -> None:
            result = await session.read_resource(_CORE_STACK_URI)
            data = json.loads(result.contents[0].text)  # type: ignore[union-attr]
            dev_deps_str = " ".join(data["dev_dependencies"])
            assert "pytest" in dev_deps_str

        await _run_resource_test(_assert)

    async def test_should_contain_linting_tool(self) -> None:
        """Validate that the JSON contains the linting configuration."""

        async def _assert(session: ClientSession) -> None:
            result = await session.read_resource(_CORE_STACK_URI)
            data = json.loads(result.contents[0].text)  # type: ignore[union-attr]
            assert data["linting"]["tool"] == "Ruff"
            assert data["linting"]["line_length"] == 100

        await _run_resource_test(_assert)

    async def test_should_contain_type_checking_config(self) -> None:
        """Validate that the JSON contains type checking configuration."""

        async def _assert(session: ClientSession) -> None:
            result = await session.read_resource(_CORE_STACK_URI)
            data = json.loads(result.contents[0].text)  # type: ignore[union-attr]
            assert data["type_checking"]["tool"] == "mypy"
            assert data["type_checking"]["mode"] == "strict"

        await _run_resource_test(_assert)

    async def test_should_contain_ci_provider(self) -> None:
        """Validate that the JSON contains the CI provider."""

        async def _assert(session: ClientSession) -> None:
            result = await session.read_resource(_CORE_STACK_URI)
            data = json.loads(result.contents[0].text)  # type: ignore[union-attr]
            assert data["ci"] == "GitHub Actions"

        await _run_resource_test(_assert)
