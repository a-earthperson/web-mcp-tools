"""Runtime settings for the standalone MCP server."""

from __future__ import annotations

from dataclasses import dataclass

from .env import get_env_int, get_env_value

_DEFAULT_LOG_LEVEL = "INFO"
_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def normalize_log_level(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in _VALID_LOG_LEVELS:
        raise ValueError(
            f"Invalid log level {value!r}; expected one of {_VALID_LOG_LEVELS}."
        )
    return normalized


@dataclass(frozen=True)
class McpServerSettings:
    host: str = "127.0.0.1"
    port: int = 8000
    mount_path: str = "/"
    sse_path: str = "/sse"
    streamable_http_path: str = "/mcp"
    log_level: str = _DEFAULT_LOG_LEVEL


def load_mcp_server_settings(
    *,
    host: str | None = None,
    port: int | None = None,
    mount_path: str | None = None,
    sse_path: str | None = None,
    streamable_http_path: str | None = None,
    log_level: str | None = None,
) -> McpServerSettings:
    resolved_log_level = get_env_value(
        "WEB_MCP_TOOLS_LOG_LEVEL", default=_DEFAULT_LOG_LEVEL
    )
    if log_level is not None:
        resolved_log_level = log_level

    return McpServerSettings(
        host=host or get_env_value("WEB_MCP_TOOLS_HOST", default="127.0.0.1"),
        port=port
        if port is not None
        else get_env_int("WEB_MCP_TOOLS_PORT", default=8000),
        mount_path=mount_path or get_env_value("WEB_MCP_TOOLS_MOUNT_PATH", default="/"),
        sse_path=sse_path or get_env_value("WEB_MCP_TOOLS_SSE_PATH", default="/sse"),
        streamable_http_path=streamable_http_path
        or get_env_value("WEB_MCP_TOOLS_STREAMABLE_HTTP_PATH", default="/mcp"),
        log_level=normalize_log_level(resolved_log_level),
    )
