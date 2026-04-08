"""MCP server surface for Firecrawl-backed web scraping."""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route

from web_mcp_tools.config.firecrawl import FirecrawlSettings, load_firecrawl_settings
from web_mcp_tools.config.server import McpServerSettings, load_mcp_server_settings
from web_mcp_tools.tools.web.scrape import WebScrapeRequestParams, web_scrape

HttpTransport = Literal["sse", "streamable-http"]

_SERVER_INSTRUCTIONS = (
    "Expose Firecrawl-backed web scraping as MCP tools with optional "
    "browser-cookie request policy."
)


async def _healthcheck(_request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def create_mcp_server(
    *,
    server_settings: McpServerSettings | None = None,
    firecrawl_settings: FirecrawlSettings | None = None,
) -> FastMCP:
    resolved_server_settings = server_settings or load_mcp_server_settings()
    resolved_firecrawl_settings = firecrawl_settings or load_firecrawl_settings()

    mcp = FastMCP(
        name="web-mcp-tools",
        instructions=_SERVER_INSTRUCTIONS,
        host=resolved_server_settings.host,
        port=resolved_server_settings.port,
        mount_path=resolved_server_settings.mount_path,
        sse_path=resolved_server_settings.sse_path,
        streamable_http_path=resolved_server_settings.streamable_http_path,
        log_level=resolved_server_settings.log_level,
        json_response=True,
    )

    @mcp.tool(
        name="web_scrape",
        description=(
            "Scrape a single URL to markdown via Firecrawl with optional browser-cookie "
            "header injection configured at server startup."
        ),
        structured_output=True,
    )
    async def web_scrape_tool(
        url: str,
        timeout_ms: int = 30000,
        wait_for_ms: int = 3000,
    ) -> dict[str, object]:
        result = await web_scrape(
            WebScrapeRequestParams(
                url=url,
                timeout_ms=timeout_ms,
                wait_for_ms=wait_for_ms,
            ),
            settings=resolved_firecrawl_settings,
        )
        return result.model_dump(mode="json")

    return mcp


def create_http_app(
    server: FastMCP,
    *,
    transport: HttpTransport,
    mount_path: str | None = None,
) -> Starlette:
    if transport == "streamable-http":
        mcp_app = server.streamable_http_app()
    else:
        mcp_app = server.sse_app(mount_path=mount_path)

    return Starlette(
        routes=[
            Route("/health", endpoint=_healthcheck),
            Route("/healthz", endpoint=_healthcheck),
            Mount("/", app=mcp_app),
        ]
    )
