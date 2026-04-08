from typing import Optional

import requests
from firecrawl.v2.types import SearchData
from firecrawl.v2.utils.error_handler import FirecrawlError
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, ValidationError

from web_mcp_tools.config.firecrawl import FirecrawlSettings, load_firecrawl_settings
from web_mcp_tools.tools.web.result import Result


class WebSearchRequestParams(BaseModel):
    """Validated search request configuration."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(description="the search query")
    sources: Optional[list[str]] = Field(
        default=None, description="source types to search, e.g. ['web', 'news']"
    )
    categories: Optional[list[str]] = Field(
        default=None, description="category filters, e.g. ['github', 'pdf']"
    )
    limit: Optional[PositiveInt] = Field(
        default=5, description="maximum number of results per source bucket"
    )
    tbs: Optional[str] = Field(
        default=None, description="time-based search filter passed through to Firecrawl"
    )
    location: Optional[str] = Field(
        default=None, description="optional search location hint"
    )
    ignore_invalid_urls: Optional[bool] = Field(
        default=None,
        description="skip invalid URLs returned by upstream search providers",
    )
    timeout_ms: Optional[PositiveInt] = Field(
        default=300000, description="search timeout in milliseconds"
    )


class WebSearchResult(Result[SearchData]):
    """Tool-safe result envelope for search outcomes."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(description="the original search query")


async def web_search(
    params: WebSearchRequestParams,
    *,
    settings: FirecrawlSettings | None = None,
) -> WebSearchResult:
    """Run a Firecrawl search and return structured result buckets."""

    runtime_settings = settings or load_firecrawl_settings()

    def fail(*, message: str) -> WebSearchResult:
        return WebSearchResult(
            query=params.query,
            payload=None,
            ok=False,
            error_message=message,
        )

    try:
        searched: SearchData = await runtime_settings.async_client().search(
            query=params.query,
            sources=params.sources,
            categories=params.categories,
            limit=params.limit,
            tbs=params.tbs,
            location=params.location,
            ignore_invalid_urls=params.ignore_invalid_urls,
            timeout=params.timeout_ms,
        )
        return WebSearchResult(query=params.query, payload=searched, ok=True)
    except ValidationError as validation:
        return fail(message=str(validation.errors()))
    except (FirecrawlError, requests.RequestException, Exception) as exc:
        return fail(message=str(exc))
