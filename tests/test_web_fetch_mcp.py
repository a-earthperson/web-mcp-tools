from __future__ import annotations

import pytest
from firecrawl.v2.types import SearchData
from starlette.testclient import TestClient

from web_mcp_tools.config.firecrawl import FirecrawlSettings
from web_mcp_tools.mcp.server import create_http_app, create_mcp_server
from web_mcp_tools.tools.web.fetch import (
    WebFetchRequestParams,
    WebFetchResult,
    web_fetch,
)
from web_mcp_tools.tools.web.search import (
    WebSearchRequestParams,
    WebSearchResult,
    web_search,
)


def test_web_fetch_request_params_normalize_timeout_and_url() -> None:
    params = WebFetchRequestParams(
        url="https://Example.com/jobs/",
        timeout_ms=1000,
        wait_for_ms=2500,
    )

    assert params.url == "https://example.com/jobs"
    assert params.timeout_ms == 5000
    assert params.wait_for_ms == 2500


@pytest.mark.asyncio
async def test_web_fetch_returns_markdown_payload() -> None:
    class _Document:
        markdown = "# hello"

    class _Client:
        async def scrape(self, **kwargs):
            assert kwargs["url"] == "https://example.com/jobs"
            assert kwargs["headers"] is None
            return _Document()

    class _Settings:
        cookies_from_browser = ""
        cookies_mode = "best_effort"

        def async_client(self) -> _Client:
            return _Client()

    result = await web_fetch(
        WebFetchRequestParams(url="https://example.com/jobs"),
        settings=_Settings(),  # type: ignore[arg-type]
    )

    assert result == WebFetchResult(
        requested_url="https://example.com/jobs",
        payload="# hello",
        ok=True,
    )


@pytest.mark.asyncio
async def test_web_fetch_returns_failure_when_client_raises() -> None:
    class _Client:
        async def scrape(self, **_kwargs):
            raise RuntimeError("boom")

    class _Settings:
        cookies_from_browser = ""
        cookies_mode = "best_effort"

        def async_client(self) -> _Client:
            return _Client()

    result = await web_fetch(
        WebFetchRequestParams(url="https://example.com/jobs"),
        settings=_Settings(),  # type: ignore[arg-type]
    )

    assert result.ok is False
    assert result.payload is None
    assert result.error_message == "boom"


@pytest.mark.asyncio
async def test_create_mcp_server_exposes_web_fetch_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_web_fetch(
        params: WebFetchRequestParams,
        *,
        settings: FirecrawlSettings | None = None,
    ) -> WebFetchResult:
        assert settings is not None
        return WebFetchResult(
            requested_url=params.url,
            payload="page markdown",
            ok=True,
        )

    monkeypatch.setattr("web_mcp_tools.mcp.server.web_fetch", _fake_web_fetch)

    server = create_mcp_server(
        firecrawl_settings=FirecrawlSettings(
            api_url="https://firecrawl.example",
            api_key="token",
        ),
    )

    tools = await server.list_tools()
    assert [tool.name for tool in tools] == ["web_fetch", "web_search"]

    result = await server.call_tool(
        "web_fetch",
        {
            "url": "https://example.com/jobs",
            "timeout_ms": 30000,
            "wait_for_ms": 3000,
        },
    )

    assert result.structured_content == {
        "requested_url": "https://example.com/jobs",
        "payload": "page markdown",
        "ok": True,
        "error_message": None,
    }


def test_web_search_request_params_normalize_query() -> None:
    params = WebSearchRequestParams(
        query="  site:example.com jobs  ",
        limit=10,
        timeout_ms=45000,
    )

    assert params.query == "site:example.com jobs"
    assert params.limit == 10
    assert params.timeout_ms == 45000


@pytest.mark.asyncio
async def test_web_search_returns_structured_payload() -> None:
    class _Client:
        async def search(self, **kwargs):
            assert kwargs["query"] == "site:example.com jobs"
            assert kwargs["sources"] == ["web"]
            assert kwargs["categories"] == ["github"]
            assert kwargs["limit"] == 3
            assert kwargs["timeout"] == 45000
            return SearchData(
                web=[{"url": "https://example.com/jobs", "title": "Jobs"}]
            )

    class _Settings:
        def async_client(self) -> _Client:
            return _Client()

    result = await web_search(
        WebSearchRequestParams(
            query="site:example.com jobs",
            sources=["web"],
            categories=["github"],
            limit=3,
            timeout_ms=45000,
        ),
        settings=_Settings(),  # type: ignore[arg-type]
    )

    assert result == WebSearchResult(
        query="site:example.com jobs",
        payload={"web": [{"url": "https://example.com/jobs", "title": "Jobs"}]},
        ok=True,
    )


@pytest.mark.asyncio
async def test_web_search_returns_failure_when_client_raises() -> None:
    class _Client:
        async def search(self, **_kwargs):
            raise RuntimeError("boom")

    class _Settings:
        def async_client(self) -> _Client:
            return _Client()

    result = await web_search(
        WebSearchRequestParams(query="site:example.com jobs"),
        settings=_Settings(),  # type: ignore[arg-type]
    )

    assert result.ok is False
    assert result.payload is None
    assert result.error_message == "boom"


@pytest.mark.asyncio
async def test_create_mcp_server_exposes_web_search_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_web_search(
        params: WebSearchRequestParams,
        *,
        settings: FirecrawlSettings | None = None,
    ) -> WebSearchResult:
        assert settings is not None
        return WebSearchResult(
            query=params.query,
            payload={"web": [{"url": "https://example.com/jobs", "title": "Jobs"}]},
            ok=True,
        )

    monkeypatch.setattr("web_mcp_tools.mcp.server.web_search", _fake_web_search)

    server = create_mcp_server(
        firecrawl_settings=FirecrawlSettings(
            api_url="https://firecrawl.example",
            api_key="token",
        ),
    )

    result = await server.call_tool(
        "web_search",
        {
            "query": "site:example.com jobs",
            "sources": ["web"],
            "categories": ["github"],
            "limit": 3,
            "timeout_ms": 45000,
        },
    )

    assert result.structured_content == {
        "query": "site:example.com jobs",
        "payload": {
            "web": [
                {
                    "url": "https://example.com/jobs",
                    "title": "Jobs",
                    "description": None,
                    "category": None,
                }
            ],
            "news": None,
            "images": None,
        },
        "ok": True,
        "error_message": None,
    }


def test_http_app_exposes_health_endpoint() -> None:
    server = create_mcp_server(
        firecrawl_settings=FirecrawlSettings(),
    )
    app = create_http_app(server, transport="streamable-http", path="/mcp")

    with TestClient(app) as client:
        response = client.get("/healthz")
        options_response = client.options("/mcp")

    assert response.status_code == 200
    assert response.text == "ok"
    assert options_response.status_code != 500
