from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from web_mcp_tools.config.firecrawl import FirecrawlSettings
from web_mcp_tools.config.server import McpServerSettings
from web_mcp_tools.mcp.server import create_http_app, create_mcp_server
from web_mcp_tools.tools.web.scrape import (
    WebScrapeRequestParams,
    WebScrapeResult,
    web_scrape,
)


def test_web_scrape_request_params_normalize_timeout_and_url() -> None:
    params = WebScrapeRequestParams(
        url="https://Example.com/jobs/",
        timeout_ms=1000,
        wait_for_ms=2500,
    )

    assert params.url == "https://example.com/jobs"
    assert params.timeout_ms == 5000
    assert params.wait_for_ms == 2500


@pytest.mark.asyncio
async def test_web_scrape_returns_markdown_payload() -> None:
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

    result = await web_scrape(
        WebScrapeRequestParams(url="https://example.com/jobs"),
        settings=_Settings(),  # type: ignore[arg-type]
    )

    assert result == WebScrapeResult(
        requested_url="https://example.com/jobs",
        payload="# hello",
        ok=True,
    )


@pytest.mark.asyncio
async def test_web_scrape_returns_failure_when_client_raises() -> None:
    class _Client:
        async def scrape(self, **_kwargs):
            raise RuntimeError("boom")

    class _Settings:
        cookies_from_browser = ""
        cookies_mode = "best_effort"

        def async_client(self) -> _Client:
            return _Client()

    result = await web_scrape(
        WebScrapeRequestParams(url="https://example.com/jobs"),
        settings=_Settings(),  # type: ignore[arg-type]
    )

    assert result.ok is False
    assert result.payload is None
    assert result.error_message == "boom"


@pytest.mark.asyncio
async def test_create_mcp_server_exposes_web_scrape_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_web_scrape(
        params: WebScrapeRequestParams,
        *,
        settings: FirecrawlSettings | None = None,
    ) -> WebScrapeResult:
        assert settings is not None
        return WebScrapeResult(
            requested_url=params.url,
            payload="page markdown",
            ok=True,
        )

    monkeypatch.setattr("web_mcp_tools.mcp.server.web_scrape", _fake_web_scrape)

    server = create_mcp_server(
        server_settings=McpServerSettings(),
        firecrawl_settings=FirecrawlSettings(
            api_url="https://firecrawl.example",
            api_key="token",
        ),
    )

    tools = await server.list_tools()
    assert [tool.name for tool in tools] == ["web_scrape"]

    result = await server.call_tool(
        "web_scrape",
        {
            "url": "https://example.com/jobs",
            "timeout_ms": 30000,
            "wait_for_ms": 3000,
        },
    )

    assert isinstance(result, tuple)
    assert result[1] == {
        "requested_url": "https://example.com/jobs",
        "payload": "page markdown",
        "ok": True,
        "error_message": None,
    }


def test_http_app_exposes_health_endpoint() -> None:
    server = create_mcp_server(
        server_settings=McpServerSettings(),
        firecrawl_settings=FirecrawlSettings(),
    )
    app = create_http_app(server, transport="streamable-http", path="/mcp")

    with TestClient(app) as client:
        response = client.get("/healthz")
        options_response = client.options("/mcp")

    assert response.status_code == 200
    assert response.text == "ok"
    assert options_response.status_code != 500
