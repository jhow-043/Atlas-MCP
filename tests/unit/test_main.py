"""Tests for the __main__ entry-point module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from atlas_mcp.__main__ import _as_transport, _parse_args, main


class TestParseArgs:
    """Tests for command-line argument parsing."""

    def test_should_default_transport_to_none(self) -> None:
        """Validate that --transport is None when not supplied."""
        args = _parse_args([])
        assert args.transport is None

    def test_should_accept_stdio_transport(self) -> None:
        """Validate that --transport stdio is accepted."""
        args = _parse_args(["--transport", "stdio"])
        assert args.transport == "stdio"

    def test_should_accept_sse_transport(self) -> None:
        """Validate that --transport sse is accepted."""
        args = _parse_args(["--transport", "sse"])
        assert args.transport == "sse"

    def test_should_reject_invalid_transport(self) -> None:
        """Validate that an invalid transport causes SystemExit."""
        with pytest.raises(SystemExit):
            _parse_args(["--transport", "grpc"])

    def test_should_exit_on_version_flag(self) -> None:
        """Validate that --version prints version and exits."""
        with pytest.raises(SystemExit) as exc_info:
            _parse_args(["--version"])
        assert exc_info.value.code == 0


class TestAsTransport:
    """Tests for the _as_transport helper."""

    def test_should_return_stdio(self) -> None:
        """Validate that 'stdio' is returned as-is."""
        assert _as_transport("stdio") == "stdio"

    def test_should_return_sse(self) -> None:
        """Validate that 'sse' is returned as-is."""
        assert _as_transport("sse") == "sse"

    def test_should_reject_invalid_value(self) -> None:
        """Validate that an invalid value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid transport"):
            _as_transport("grpc")


class TestMainFunction:
    """Tests for the main() orchestrator function."""

    @patch("atlas_mcp.__main__._async_main")
    @patch("atlas_mcp.__main__.setup_logging")
    @patch("atlas_mcp.__main__.Settings.from_env")
    def test_should_run_without_error(
        self,
        mock_settings: MagicMock,
        mock_logging: MagicMock,
        mock_async_main: MagicMock,
    ) -> None:
        """Validate that main(argv=[]) completes without exceptions."""
        mock_settings.return_value = MagicMock(
            log_level="INFO", log_format="text", transport="stdio"
        )
        main(argv=[])

        mock_settings.assert_called_once()
        mock_logging.assert_called_once_with("INFO", "text")

    @patch("atlas_mcp.__main__._async_main")
    @patch("atlas_mcp.__main__.setup_logging")
    @patch("atlas_mcp.__main__.Settings.from_env")
    def test_should_override_transport_from_cli(
        self,
        mock_settings: MagicMock,
        mock_logging: MagicMock,
        mock_async_main: MagicMock,
    ) -> None:
        """Validate that --transport flag overrides the env var."""
        mock_env_settings = MagicMock(
            log_level="INFO",
            log_format="text",
            transport="stdio",
            db=MagicMock(),
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
            embedding_dimension=1536,
            openai_api_key=None,
            sse_host="0.0.0.0",  # noqa: S104
            sse_port=8000,
        )
        mock_settings.return_value = mock_env_settings

        main(argv=["--transport", "sse"])

        # asyncio.run is called with _async_main whose settings have transport=sse
        # Because transport is overridden, a new Settings is created
        call_args = mock_async_main.call_args
        settings_arg = call_args[0][0]
        assert settings_arg.transport == "sse"

    @patch("atlas_mcp.__main__._async_main")
    @patch("atlas_mcp.__main__.setup_logging")
    @patch("atlas_mcp.__main__.Settings.from_env")
    def test_should_keep_env_transport_when_no_cli_flag(
        self,
        mock_settings: MagicMock,
        mock_logging: MagicMock,
        mock_async_main: MagicMock,
    ) -> None:
        """Validate that without --transport, env var transport is used."""
        mock_env_settings = MagicMock(log_level="DEBUG", log_format="json", transport="sse")
        mock_settings.return_value = mock_env_settings

        main(argv=[])

        call_args = mock_async_main.call_args
        settings_arg = call_args[0][0]
        assert settings_arg.transport == "sse"

    @patch("atlas_mcp.__main__._async_main")
    @patch("atlas_mcp.__main__.setup_logging")
    @patch("atlas_mcp.__main__.Settings.from_env")
    def test_should_handle_keyboard_interrupt(
        self,
        mock_settings: MagicMock,
        mock_logging: MagicMock,
        mock_async_main: MagicMock,
    ) -> None:
        """Validate that KeyboardInterrupt is caught gracefully."""
        mock_settings.return_value = MagicMock(
            log_level="INFO", log_format="text", transport="stdio"
        )
        mock_async_main.side_effect = KeyboardInterrupt

        # Should NOT propagate
        main(argv=[])


class TestAsyncMain:
    """Tests for the _async_main coroutine."""

    @pytest.mark.asyncio
    @patch("atlas_mcp.__main__.ProtocolHandler")
    async def test_should_call_bootstrap_startup_and_shutdown(
        self,
        mock_handler_cls: MagicMock,
    ) -> None:
        """Validate that _async_main calls startup then shutdown."""
        from atlas_mcp.__main__ import _async_main

        settings = MagicMock(transport="stdio")
        bootstrap = AsyncMock()

        mock_handler = MagicMock()
        mock_handler.run_async = AsyncMock()
        mock_handler_cls.return_value = mock_handler

        await _async_main(settings, bootstrap)

        bootstrap.startup.assert_awaited_once_with(settings)
        bootstrap.shutdown.assert_awaited_once()
        mock_handler.run_async.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("atlas_mcp.__main__.ProtocolHandler")
    async def test_should_shutdown_even_on_error(
        self,
        mock_handler_cls: MagicMock,
    ) -> None:
        """Validate that shutdown is called even if startup raises."""
        from atlas_mcp.__main__ import _async_main

        settings = MagicMock(transport="stdio")
        bootstrap = AsyncMock()
        bootstrap.startup.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await _async_main(settings, bootstrap)

        bootstrap.shutdown.assert_awaited_once()
