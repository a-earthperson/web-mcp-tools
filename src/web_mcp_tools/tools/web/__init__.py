"""Firecrawl-backed web helpers."""

from __future__ import annotations

from .fetch import WebFetchRequestParams, WebFetchResult, web_fetch
from .search import WebSearchRequestParams, WebSearchResult, web_search

__all__ = [
    "WebFetchRequestParams",
    "WebFetchResult",
    "WebSearchRequestParams",
    "WebSearchResult",
    "web_fetch",
    "web_search",
]
