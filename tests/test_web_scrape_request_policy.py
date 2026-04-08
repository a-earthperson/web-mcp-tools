from __future__ import annotations

import pytest

from web_mcp_tools.tools.web.cookies import BrowserRequestOverrides
from web_mcp_tools.tools.web.request_policy import (
    WebScrapeHeaderConfig,
    WebScrapePolicyResolver,
)


def test_resolver_returns_empty_headers_when_no_browser_cookies_selector() -> None:
    resolver = WebScrapePolicyResolver(WebScrapeHeaderConfig())

    policy = resolver.resolve(target_url="https://example.com/jobs")

    assert policy.headers == {}
    assert policy.cookies_mode == "best_effort"
    assert policy.used_browser_cookies is False
    assert policy.fallback_reason == "no browser cookie selector configured"


def test_resolver_returns_empty_headers_when_mode_is_off_even_with_selector() -> None:
    resolver = WebScrapePolicyResolver(
        WebScrapeHeaderConfig(cookies_from_browser="safari", cookies_mode="off")
    )

    policy = resolver.resolve(target_url="https://example.com/private")

    assert policy.headers == {}
    assert policy.cookies_mode == "off"
    assert policy.used_browser_cookies is False
    assert policy.fallback_reason == "browser cookie injection disabled"


def test_resolver_applies_browser_cookie_and_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_browser_overrides(
        *, cookies_from_browser: str, target_url: str
    ) -> BrowserRequestOverrides:
        assert cookies_from_browser == "safari"
        assert target_url == "https://example.com/private"
        return BrowserRequestOverrides(
            cookie_header="session=abc",
            user_agent="browser-agent/2.0",
        )

    monkeypatch.setattr(
        "web_mcp_tools.tools.web.request_policy.build_browser_request_overrides",
        _fake_browser_overrides,
    )

    resolver = WebScrapePolicyResolver(
        WebScrapeHeaderConfig(
            cookies_from_browser="safari",
        )
    )

    policy = resolver.resolve(target_url="https://example.com/private")

    assert policy.headers["Cookie"] == "session=abc"
    assert policy.headers["User-Agent"] == "browser-agent/2.0"
    assert policy.used_browser_cookies is True
    assert policy.fallback_reason is None


def test_resolver_best_effort_falls_back_when_browser_cookie_resolution_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_browser_overrides(
        *, cookies_from_browser: str, target_url: str
    ) -> BrowserRequestOverrides:
        raise RuntimeError("browser unavailable")

    monkeypatch.setattr(
        "web_mcp_tools.tools.web.request_policy.build_browser_request_overrides",
        _raise_browser_overrides,
    )

    resolver = WebScrapePolicyResolver(
        WebScrapeHeaderConfig(
            cookies_from_browser="safari",
        )
    )

    policy = resolver.resolve(target_url="https://example.com/private")
    assert policy.headers == {}
    assert policy.used_browser_cookies is False
    assert policy.fallback_reason is not None
    assert "browser unavailable" in policy.fallback_reason


def test_resolver_required_raises_when_browser_cookie_resolution_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_browser_overrides(
        *, cookies_from_browser: str, target_url: str
    ) -> BrowserRequestOverrides:
        raise RuntimeError("browser unavailable")

    monkeypatch.setattr(
        "web_mcp_tools.tools.web.request_policy.build_browser_request_overrides",
        _raise_browser_overrides,
    )

    resolver = WebScrapePolicyResolver(
        WebScrapeHeaderConfig(cookies_from_browser="safari", cookies_mode="required")
    )

    with pytest.raises(RuntimeError, match="browser unavailable"):
        resolver.resolve(target_url="https://example.com/private")


def test_resolver_best_effort_falls_back_when_required_cookie_header_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _overrides_without_cookies(
        *, cookies_from_browser: str, target_url: str
    ) -> BrowserRequestOverrides:
        return BrowserRequestOverrides(cookie_header="", user_agent="browser-agent/2.0")

    monkeypatch.setattr(
        "web_mcp_tools.tools.web.request_policy.build_browser_request_overrides",
        _overrides_without_cookies,
    )

    resolver = WebScrapePolicyResolver(
        WebScrapeHeaderConfig(cookies_from_browser="safari")
    )

    policy = resolver.resolve(target_url="https://example.com/private")
    assert policy.headers == {}
    assert policy.used_browser_cookies is False
    assert policy.fallback_reason is not None
    assert "no matching cookie pairs were resolved" in policy.fallback_reason


def test_resolver_required_raises_when_selector_missing() -> None:
    resolver = WebScrapePolicyResolver(
        WebScrapeHeaderConfig(cookies_from_browser="", cookies_mode="required")
    )

    with pytest.raises(
        ValueError,
        match="Cookie mode is 'required' but no --cookies-from-browser selector was configured.",
    ):
        resolver.resolve(target_url="https://example.com/private")


def test_resolver_required_raises_when_required_cookie_header_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _overrides_without_cookies(
        *, cookies_from_browser: str, target_url: str
    ) -> BrowserRequestOverrides:
        return BrowserRequestOverrides(cookie_header="", user_agent="browser-agent/2.0")

    monkeypatch.setattr(
        "web_mcp_tools.tools.web.request_policy.build_browser_request_overrides",
        _overrides_without_cookies,
    )

    resolver = WebScrapePolicyResolver(
        WebScrapeHeaderConfig(cookies_from_browser="safari", cookies_mode="required")
    )

    with pytest.raises(ValueError, match="no matching cookie pairs were resolved"):
        resolver.resolve(target_url="https://example.com/private")


def test_resolver_raises_when_cookies_mode_is_invalid() -> None:
    resolver = WebScrapePolicyResolver(
        WebScrapeHeaderConfig(cookies_from_browser="safari", cookies_mode="nope")  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="Invalid cookies mode"):
        resolver.resolve(target_url="https://example.com/private")
