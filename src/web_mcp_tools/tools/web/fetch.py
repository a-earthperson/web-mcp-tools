from math import ceil
from typing import Optional

import requests
from firecrawl.v2.types import Document
from firecrawl.v2.utils.error_handler import FirecrawlError
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    ValidationError,
    model_validator,
)

from web_mcp_tools.config.firecrawl import FirecrawlSettings, load_firecrawl_settings
from web_mcp_tools.tools.web.request_policy import (
    WebFetchHeaderConfig,
    WebFetchPolicyResolver,
)
from web_mcp_tools.tools.web.result import Result
from web_mcp_tools.url import Url


def _build_policy_resolver(settings: FirecrawlSettings) -> WebFetchPolicyResolver:
    """Build a resolver from current runtime configuration."""

    return WebFetchPolicyResolver(
        WebFetchHeaderConfig(
            cookies_from_browser=settings.cookies_from_browser,
            cookies_mode=settings.cookies_mode,
        )
    )


class WebFetchRequestParams(BaseModel):
    """Validated fetch request configuration."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    url: Url = Field(description="the URL to fetch")
    timeout_ms: Optional[PositiveInt] = Field(
        default=30000, description="request timeout in milliseconds"
    )
    wait_for_ms: Optional[NonNegativeInt] = Field(
        default=3000, description="time to wait for page render in milliseconds"
    )

    @model_validator(mode="after")
    def timeout_at_least_twice_wait(self) -> "WebFetchRequestParams":
        """Guarantee timeout >= 2 * wait_for_ms."""

        wait = self.wait_for_ms or 0
        min_timeout = max(1, ceil(2.0 * wait))
        current = self.timeout_ms or min_timeout
        self.timeout_ms = max(min_timeout, current)
        return self


class WebFetchResult(Result[str]):
    """Tool-safe result envelope for fetch outcomes."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    requested_url: Url = Field(description="source/fetched url")


async def web_fetch(
    params: WebFetchRequestParams,
    *,
    settings: FirecrawlSettings | None = None,
) -> WebFetchResult:
    """Fetch a single URL via Firecrawl and return a structured result."""

    runtime_settings = settings or load_firecrawl_settings()

    def fail(*, message: str) -> WebFetchResult:
        return WebFetchResult(
            requested_url=params.url,
            payload=None,
            ok=False,
            error_message=message,
        )

    try:
        request_policy = _build_policy_resolver(runtime_settings).resolve(
            target_url=params.url
        )
        fetched: Document = await runtime_settings.async_client().scrape(
            url=params.url,
            timeout=params.timeout_ms,
            only_main_content=False,
            remove_base64_images=True,
            wait_for=params.wait_for_ms,
            formats=["markdown"],
            headers=request_policy.headers or None,
        )
        return WebFetchResult(
            requested_url=params.url, payload=fetched.markdown, ok=True
        )
    except ValidationError as validation:
        return fail(message=str(validation.errors()))
    except (FirecrawlError, requests.RequestException, Exception) as exc:
        return fail(message=str(exc))
