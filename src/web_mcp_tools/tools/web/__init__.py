"""Firecrawl-backed web scrape helpers."""

from .result import Result
from .scrape import WebScrapeRequestParams, WebScrapeResult, web_scrape

__all__ = [
    "Result",
    "WebScrapeRequestParams",
    "WebScrapeResult",
    "web_scrape",
]
