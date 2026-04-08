"""Composable request policy for Firecrawl-backed web fetching."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, cast

from web_mcp_tools.tools.web.cookies import build_browser_request_overrides

CookiesMode = Literal["off", "best_effort", "required"]
_VALID_COOKIES_MODES: set[str] = {"off", "best_effort", "required"}


@dataclass(frozen=True)
class WebFetchHeaderConfig:
    """Settings used to build per-request headers."""

    cookies_from_browser: str = ""
    cookies_mode: CookiesMode = "best_effort"


@dataclass(frozen=True)
class WebFetchRequestPolicy:
    """Resolved policy for one fetch request."""

    headers: dict[str, str] = field(default_factory=dict)
    cookies_mode: CookiesMode = "best_effort"
    used_browser_cookies: bool = False
    fallback_reason: str | None = None


class WebFetchPolicyResolver:
    """Resolve deterministic request headers for one target URL."""

    def __init__(self, config: WebFetchHeaderConfig):
        self._config = config

    def resolve(
        self,
        *,
        target_url: str,
    ) -> WebFetchRequestPolicy:
        mode = self._normalized_mode()
        headers: dict[str, str] = {}
        cookie_selector = self._config.cookies_from_browser.strip()

        if mode == "off":
            return WebFetchRequestPolicy(
                headers=headers,
                cookies_mode=mode,
                fallback_reason="browser cookie injection disabled",
            )
        if not cookie_selector:
            if mode == "required":
                raise ValueError(
                    "Cookie mode is 'required' but no --cookies-from-browser selector was configured."
                )
            return WebFetchRequestPolicy(
                headers=headers,
                cookies_mode=mode,
                fallback_reason="no browser cookie selector configured",
            )

        try:
            overrides = build_browser_request_overrides(
                cookies_from_browser=cookie_selector,
                target_url=target_url,
            )
        except Exception as exc:
            if mode == "required":
                raise
            return WebFetchRequestPolicy(
                headers=headers,
                cookies_mode=mode,
                fallback_reason=f"browser cookie resolution failed: {exc}",
            )
        if not overrides.cookie_header or not overrides.user_agent:
            if not overrides.cookie_header:
                reason = "Browser cookies were requested but no matching cookie pairs were resolved."
            else:
                reason = (
                    "Browser cookies were requested but no user-agent was resolved."
                )
            if mode == "required":
                raise ValueError(reason)
            return WebFetchRequestPolicy(
                headers=headers,
                cookies_mode=mode,
                fallback_reason=reason,
            )
        headers["Cookie"] = overrides.cookie_header
        headers["User-Agent"] = overrides.user_agent

        return WebFetchRequestPolicy(
            headers=headers,
            cookies_mode=mode,
            used_browser_cookies=True,
        )

    def _normalized_mode(self) -> CookiesMode:
        mode = self._config.cookies_mode.strip().lower()
        if mode not in _VALID_COOKIES_MODES:
            raise ValueError(
                f"Invalid cookies mode {self._config.cookies_mode!r}; expected one of {_VALID_COOKIES_MODES}."
            )
        return cast(CookiesMode, mode)
