"""CLI entrypoints for web-mcp-tools."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from web_mcp_tools.config.firecrawl import load_firecrawl_settings
from web_mcp_tools.config.server import load_mcp_server_settings
from web_mcp_tools.mcp.server import create_mcp_server


class _HealthHandler(BaseHTTPRequestHandler):
    def log_message(self, _fmt: str, *_args: Any) -> None:
        pass

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/healthz", "/health"):
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)


def _serve(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), _HealthHandler)
    server.serve_forever()


def build_parser() -> argparse.ArgumentParser:
    server_defaults = load_mcp_server_settings()
    firecrawl_defaults = load_firecrawl_settings()

    parser = argparse.ArgumentParser(prog="web-mcp-tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_mcp = sub.add_parser("mcp", help="Run the web scrape MCP server")
    p_mcp.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport to expose.",
    )
    p_mcp.add_argument("--host", default=server_defaults.host)
    p_mcp.add_argument("--port", type=int, default=server_defaults.port)
    p_mcp.add_argument("--mount-path", default=server_defaults.mount_path)
    p_mcp.add_argument("--sse-path", default=server_defaults.sse_path)
    p_mcp.add_argument(
        "--streamable-http-path",
        default=server_defaults.streamable_http_path,
    )
    p_mcp.add_argument("--log-level", default=server_defaults.log_level)
    p_mcp.add_argument(
        "--cookies-from-browser",
        nargs="?",
        const="safari",
        default=firecrawl_defaults.cookies_from_browser,
        help=(
            "Extract Cookie/User-Agent from a local browser profile for authenticated "
            "scrapes. Format: <browser> or <browser>:/path/to/profile/file. "
            "Currently implemented: safari on macOS (Cookies.binarycookies)."
        ),
    )
    p_mcp.add_argument(
        "--cookies-mode",
        choices=["off", "best_effort", "required"],
        default=firecrawl_defaults.cookies_mode,
        help=(
            "Cookie injection policy when --cookies-from-browser is set. "
            "'best_effort' attempts injection and falls back to no headers on "
            "resolution failures; 'required' fails when browser cookies cannot be "
            "resolved for the target URL."
        ),
    )

    p_serve = sub.add_parser(
        "serve", help="Run a minimal HTTP server (e.g. Docker health checks)"
    )
    p_serve.add_argument("--host", default=server_defaults.host)
    p_serve.add_argument("--port", type=int, default=server_defaults.port)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "serve":
        _serve(args.host, args.port)
        return

    server_settings = load_mcp_server_settings(
        host=args.host,
        port=args.port,
        mount_path=args.mount_path,
        sse_path=args.sse_path,
        streamable_http_path=args.streamable_http_path,
        log_level=args.log_level,
    )
    firecrawl_settings = load_firecrawl_settings(
        cookies_from_browser=args.cookies_from_browser,
        cookies_mode=args.cookies_mode,
    )
    server = create_mcp_server(
        server_settings=server_settings,
        firecrawl_settings=firecrawl_settings,
    )

    if args.transport == "stdio":
        server.run(transport="stdio")
        return

    path = (
        server_settings.sse_path
        if args.transport == "sse"
        else server_settings.streamable_http_path
    )
    server.run(
        transport=args.transport,
        host=server_settings.host,
        port=server_settings.port,
        log_level=server_settings.log_level.lower(),
        path=path,
    )
