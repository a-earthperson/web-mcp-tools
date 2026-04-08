from __future__ import annotations

import sys

import pytest

from web_mcp_tools import cli
from web_mcp_tools.config.firecrawl import load_firecrawl_settings
from web_mcp_tools.config.server import load_mcp_server_settings


class _FakeServer:
    def __init__(self) -> None:
        self.run_calls: list[dict[str, object]] = []

    def run(self, **kwargs: object) -> None:
        self.run_calls.append(kwargs)


def test_load_mcp_server_settings_reads_valid_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEB_MCP_TOOLS_HOST", "0.0.0.0")
    monkeypatch.setenv("WEB_MCP_TOOLS_PORT", "9000")
    monkeypatch.setenv("WEB_MCP_TOOLS_MOUNT_PATH", "/")
    monkeypatch.setenv("WEB_MCP_TOOLS_SSE_PATH", "/events")
    monkeypatch.setenv("WEB_MCP_TOOLS_STREAMABLE_HTTP_PATH", "/rpc")
    monkeypatch.setenv("WEB_MCP_TOOLS_LOG_LEVEL", "debug")

    settings = load_mcp_server_settings()

    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.mount_path == "/"
    assert settings.sse_path == "/events"
    assert settings.streamable_http_path == "/rpc"
    assert settings.log_level == "DEBUG"


def test_load_firecrawl_settings_reads_valid_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIRECRAWL_BASE_URL", "https://firecrawl.example")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "token")
    monkeypatch.setenv("WEB_MCP_TOOLS_COOKIES_FROM_BROWSER", "safari")
    monkeypatch.setenv("WEB_MCP_TOOLS_COOKIES_MODE", "required")

    settings = load_firecrawl_settings()

    assert settings.api_url == "https://firecrawl.example"
    assert settings.api_key == "token"
    assert settings.cookies_from_browser == "safari"
    assert settings.cookies_mode == "required"


def test_load_mcp_server_settings_rejects_invalid_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEB_MCP_TOOLS_PORT", "not-an-int")

    with pytest.raises(ValueError, match="WEB_MCP_TOOLS_PORT"):
        load_mcp_server_settings()

    monkeypatch.setenv("WEB_MCP_TOOLS_PORT", "8000")
    monkeypatch.setenv("WEB_MCP_TOOLS_LOG_LEVEL", "loud")

    with pytest.raises(ValueError, match="Invalid log level"):
        load_mcp_server_settings()


def test_load_firecrawl_settings_rejects_invalid_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEB_MCP_TOOLS_COOKIES_MODE", "sometimes")

    with pytest.raises(ValueError, match="Invalid cookies mode"):
        load_firecrawl_settings()


def test_main_uses_env_var_defaults_for_http_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_server = _FakeServer()
    captured: dict[str, object] = {}

    def _create_mcp_server(*, firecrawl_settings):
        captured["firecrawl_settings"] = firecrawl_settings
        return fake_server

    monkeypatch.setenv("WEB_MCP_TOOLS_HOST", "0.0.0.0")
    monkeypatch.setenv("WEB_MCP_TOOLS_PORT", "9000")
    monkeypatch.setenv("WEB_MCP_TOOLS_STREAMABLE_HTTP_PATH", "/rpc")
    monkeypatch.setenv("WEB_MCP_TOOLS_LOG_LEVEL", "debug")
    monkeypatch.setenv("WEB_MCP_TOOLS_COOKIES_FROM_BROWSER", "safari")
    monkeypatch.setenv("WEB_MCP_TOOLS_COOKIES_MODE", "required")
    monkeypatch.setattr(
        cli,
        "create_mcp_server",
        _create_mcp_server,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["web-mcp-tools", "mcp", "--transport", "streamable-http"],
    )

    cli.main()

    firecrawl_settings = captured["firecrawl_settings"]
    assert firecrawl_settings.cookies_from_browser == "safari"
    assert firecrawl_settings.cookies_mode == "required"
    assert fake_server.run_calls == [
        {
            "transport": "streamable-http",
            "host": "0.0.0.0",
            "port": 9000,
            "log_level": "debug",
            "path": "/rpc",
            "json_response": True,
        }
    ]


def test_main_cli_args_override_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_server = _FakeServer()
    captured: dict[str, object] = {}

    def _create_mcp_server(*, firecrawl_settings):
        captured["firecrawl_settings"] = firecrawl_settings
        return fake_server

    monkeypatch.setenv("WEB_MCP_TOOLS_HOST", "127.0.0.1")
    monkeypatch.setenv("WEB_MCP_TOOLS_PORT", "8000")
    monkeypatch.setenv("WEB_MCP_TOOLS_STREAMABLE_HTTP_PATH", "/env")
    monkeypatch.setenv("WEB_MCP_TOOLS_LOG_LEVEL", "warning")
    monkeypatch.setenv("WEB_MCP_TOOLS_COOKIES_FROM_BROWSER", "env-browser")
    monkeypatch.setenv("WEB_MCP_TOOLS_COOKIES_MODE", "best_effort")
    monkeypatch.setattr(
        cli,
        "create_mcp_server",
        _create_mcp_server,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "web-mcp-tools",
            "mcp",
            "--transport",
            "streamable-http",
            "--host",
            "0.0.0.0",
            "--port",
            "9100",
            "--streamable-http-path",
            "/cli",
            "--log-level",
            "error",
            "--cookies-from-browser",
            "safari",
            "--cookies-mode",
            "required",
        ],
    )

    cli.main()

    firecrawl_settings = captured["firecrawl_settings"]
    assert firecrawl_settings.cookies_from_browser == "safari"
    assert firecrawl_settings.cookies_mode == "required"
    assert fake_server.run_calls == [
        {
            "transport": "streamable-http",
            "host": "0.0.0.0",
            "port": 9100,
            "log_level": "error",
            "path": "/cli",
            "json_response": True,
        }
    ]
