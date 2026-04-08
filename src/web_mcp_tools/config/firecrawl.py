"""Standalone Firecrawl settings for web fetch tools."""

from __future__ import annotations

from dataclasses import dataclass

from firecrawl import AsyncFirecrawl, Firecrawl

from .env import get_env_value, get_secret_env_value

_DEFAULT_COOKIES_MODE = "best_effort"
_VALID_COOKIES_MODES = {"off", "best_effort", "required"}


def normalize_cookies_mode(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in _VALID_COOKIES_MODES:
        raise ValueError(
            f"Invalid cookies mode {value!r}; expected one of {_VALID_COOKIES_MODES}."
        )
    return normalized


@dataclass(frozen=True)
class FirecrawlSettings:
    """Settings for connecting to a Firecrawl deployment."""

    api_url: str = ""
    api_key: str = ""
    cookies_from_browser: str = ""
    cookies_mode: str = _DEFAULT_COOKIES_MODE

    def client(self) -> Firecrawl:
        if not self.api_url:
            raise ValueError(
                "FIRECRAWL_BASE_URL not set. Configure FIRECRAWL_BASE_URL to use Firecrawl tools."
            )
        return Firecrawl(api_url=self.api_url, api_key=self.api_key)

    def async_client(self) -> AsyncFirecrawl:
        if not self.api_url:
            raise ValueError(
                "FIRECRAWL_BASE_URL not set. Configure FIRECRAWL_BASE_URL to use Firecrawl tools."
            )
        return AsyncFirecrawl(api_url=self.api_url, api_key=self.api_key)


def load_firecrawl_settings(
    *,
    cookies_from_browser: str | None = None,
    cookies_mode: str | None = None,
) -> FirecrawlSettings:
    resolved_cookies_from_browser = get_env_value(
        "WEB_MCP_TOOLS_COOKIES_FROM_BROWSER",
        default="",
    )
    if cookies_from_browser is not None:
        resolved_cookies_from_browser = cookies_from_browser.strip()

    resolved_cookies_mode = get_env_value(
        "WEB_MCP_TOOLS_COOKIES_MODE",
        default=_DEFAULT_COOKIES_MODE,
    )
    if cookies_mode is not None:
        resolved_cookies_mode = cookies_mode

    return FirecrawlSettings(
        api_url=get_env_value("FIRECRAWL_BASE_URL", default=""),
        api_key=get_secret_env_value("FIRECRAWL_API_KEY"),
        cookies_from_browser=resolved_cookies_from_browser,
        cookies_mode=normalize_cookies_mode(resolved_cookies_mode),
    )
