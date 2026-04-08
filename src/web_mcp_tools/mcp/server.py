"""MCP server surface for Firecrawl-backed web scraping."""

from __future__ import annotations

from typing import Literal

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse

from web_mcp_tools.config.firecrawl import FirecrawlSettings, load_firecrawl_settings
from web_mcp_tools.tools.web.scrape import WebScrapeRequestParams, web_scrape

HttpTransport = Literal["sse", "streamable-http"]

_SERVER_INSTRUCTIONS = (
    "Expose Firecrawl-backed web scraping as MCP tools with optional "
    "browser-cookie request policy."
)


def create_mcp_server(
    *,
    firecrawl_settings: FirecrawlSettings | None = None,
) -> FastMCP:
    resolved_firecrawl_settings = firecrawl_settings or load_firecrawl_settings()

    mcp = FastMCP(
        name="web-mcp-tools",
        instructions=_SERVER_INSTRUCTIONS,
    )

    @mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
    async def healthcheck(_request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    @mcp.custom_route("/healthz", methods=["GET"], include_in_schema=False)
    async def healthcheck_z(_request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    @mcp.tool(
        name="web_scrape",
        description=(
            "Scrape a single URL to markdown via Firecrawl with optional browser-cookie "
            "header injection configured at server startup."
        ),
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
    path: str | None = None,
) -> Starlette:
    return server.http_app(
        path=path,
        transport=transport,
        json_response=True,
    )
