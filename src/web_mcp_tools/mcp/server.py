"""MCP server surface for Firecrawl-backed web tools."""

from __future__ import annotations

from typing import Literal

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse

from web_mcp_tools.config.firecrawl import FirecrawlSettings, load_firecrawl_settings
from web_mcp_tools.tools.web.fetch import WebFetchRequestParams, web_fetch
from web_mcp_tools.tools.web.search import WebSearchRequestParams, web_search

HttpTransport = Literal["sse", "streamable-http"]

_SERVER_INSTRUCTIONS = (
    "Expose Firecrawl-backed web fetch and search functionality as MCP tools, "
    "with optional browser-cookie request policy for fetch."
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
        name="web_fetch",
        description=(
            "Fetch a single URL to markdown via Firecrawl with optional browser-cookie "
            "header injection configured at server startup."
        ),
    )
    async def web_fetch_tool(
        url: str,
        timeout_ms: int = 30000,
        wait_for_ms: int = 3000,
    ) -> dict[str, object]:
        result = await web_fetch(
            WebFetchRequestParams(
                url=url,
                timeout_ms=timeout_ms,
                wait_for_ms=wait_for_ms,
            ),
            settings=resolved_firecrawl_settings,
        )
        return result.model_dump(mode="json")

    @mcp.tool(
        name="web_search",
        description=(
            "Run a Firecrawl search and return structured result buckets grouped "
            "by source type."
        ),
    )
    async def web_search_tool(
        query: str,
        sources: list[str] | None = None,
        categories: list[str] | None = None,
        limit: int = 5,
        tbs: str | None = None,
        location: str | None = None,
        ignore_invalid_urls: bool | None = None,
        timeout_ms: int = 300000,
    ) -> dict[str, object]:
        result = await web_search(
            WebSearchRequestParams(
                query=query,
                sources=sources,
                categories=categories,
                limit=limit,
                tbs=tbs,
                location=location,
                ignore_invalid_urls=ignore_invalid_urls,
                timeout_ms=timeout_ms,
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
