"""Browser cookie extraction helpers with OS/browser delegation."""

from __future__ import annotations

import platform
import plistlib
import struct
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit


@dataclass(frozen=True)
class BrowserRequestOverrides:
    """Per-request overrides sourced from a local browser profile."""

    cookie_header: str = ""
    user_agent: str = ""


@dataclass(frozen=True)
class _BrowserSelection:
    browser: str
    custom_path: str | None = None


_Extractor = Callable[[str, _BrowserSelection], BrowserRequestOverrides]


def build_browser_request_overrides(
    *,
    cookies_from_browser: str,
    target_url: str,
) -> BrowserRequestOverrides:
    """Resolve browser-backed Cookie/User-Agent overrides for one URL."""

    selection = _parse_browser_selection(cookies_from_browser)
    system = platform.system().strip().lower()
    extractor = _resolve_extractor(system=system, browser=selection.browser)
    return extractor(target_url, selection)


def _parse_browser_selection(raw: str) -> _BrowserSelection:
    value = raw.strip()
    if not value:
        raise ValueError("--cookies-from-browser requires a browser value.")

    browser = value
    custom_path: str | None = None
    if ":" in value:
        browser, custom_path = value.split(":", 1)
        custom_path = custom_path.strip() or None
    browser = browser.strip().lower()
    if not browser:
        raise ValueError("--cookies-from-browser requires a browser value.")
    return _BrowserSelection(browser=browser, custom_path=custom_path)


def _resolve_extractor(*, system: str, browser: str) -> _Extractor:
    matrix: dict[tuple[str, str], _Extractor] = {
        ("darwin", "safari"): _extract_darwin_safari,
        ("darwin", "chrome"): _unsupported_extractor,
        ("darwin", "chromium"): _unsupported_extractor,
        ("darwin", "edge"): _unsupported_extractor,
        ("darwin", "firefox"): _unsupported_extractor,
        ("linux", "chrome"): _unsupported_extractor,
        ("linux", "chromium"): _unsupported_extractor,
        ("linux", "edge"): _unsupported_extractor,
        ("linux", "firefox"): _unsupported_extractor,
        ("windows", "chrome"): _unsupported_extractor,
        ("windows", "chromium"): _unsupported_extractor,
        ("windows", "edge"): _unsupported_extractor,
        ("windows", "firefox"): _unsupported_extractor,
    }
    extractor = matrix.get((system, browser))
    if extractor is None:
        return _unsupported_extractor
    return extractor


def _unsupported_extractor(
    _target_url: str, selection: _BrowserSelection
) -> BrowserRequestOverrides:
    system = platform.system()
    browser = selection.browser
    raise NotImplementedError(
        "Browser cookie extraction is implemented only for Safari on macOS. "
        f"Received browser={browser!r} on os={system!r}. "
        "Non-trivial drift exists across browser/OS stacks: Safari uses "
        "Cookies.binarycookies, Chromium-family browsers use encrypted SQLite "
        "storage plus OS keychain APIs (DPAPI/Keychain/libsecret), and Firefox "
        "profile resolution and cookie stores differ across platforms."
    )


def _extract_darwin_safari(
    target_url: str, selection: _BrowserSelection
) -> BrowserRequestOverrides:
    target = urlsplit(target_url)
    host = (target.hostname or "").lower()
    if not host:
        raise ValueError(f"Target URL has no host: {target_url!r}")
    request_path = target.path or "/"
    is_https = target.scheme.lower() == "https"

    candidate_paths: list[Path] = []
    if selection.custom_path:
        candidate_paths.append(Path(selection.custom_path).expanduser())
    else:
        candidate_paths.extend(
            [
                Path("~/Library/Cookies/Cookies.binarycookies").expanduser(),
                Path(
                    "~/Library/Containers/com.apple.Safari/Data/Library/Cookies/Cookies.binarycookies"
                ).expanduser(),
            ]
        )
    safari_path = next((path for path in candidate_paths if path.is_file()), None)
    if safari_path is None:
        raise FileNotFoundError(
            "Could not find Safari cookies file; provide "
            "--cookies-from-browser safari:/path/to/Cookies.binarycookies."
        )

    raw = safari_path.read_bytes()
    records = _load_safari_cookie_records(raw)
    now = int(time.time())
    pairs: list[str] = []
    seen_names: set[str] = set()

    for record in records:
        name = (record.get("name") or "").strip()
        value = record.get("value") or ""
        domain = (record.get("domain") or "").strip().lower()
        cookie_path = (record.get("path") or "/") or "/"
        expires = int(record.get("expires") or 0)
        secure = bool(record.get("secure"))

        if not name:
            continue
        if expires and expires < now:
            continue
        if secure and not is_https:
            continue
        if not _domain_matches(host, domain):
            continue
        if not request_path.startswith(cookie_path):
            continue
        if name in seen_names:
            continue

        seen_names.add(name)
        pairs.append(f"{name}={value}")

    return BrowserRequestOverrides(
        cookie_header="; ".join(pairs),
        user_agent=_detect_safari_user_agent(),
    )


def _domain_matches(host: str, cookie_domain: str) -> bool:
    if cookie_domain.startswith("."):
        bare = cookie_domain[1:]
        return host == bare or host.endswith(f".{bare}")
    return host == cookie_domain


def _detect_safari_user_agent() -> str:
    """Detect Safari UA from local install/config; fallback to a safe default."""

    try:
        custom = subprocess.check_output(
            ["defaults", "read", "com.apple.Safari", "CustomUserAgent"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if custom:
            return custom
    except Exception:
        pass

    safari_version = "17.0"
    info_plist = Path("/Applications/Safari.app/Contents/Info.plist")
    try:
        with info_plist.open("rb") as file_handle:
            info = plistlib.load(file_handle)
        version = str(info.get("CFBundleShortVersionString", "")).strip()
        if version:
            safari_version = version
    except Exception:
        pass

    mac_ver = platform.mac_ver()[0] or "10.15.7"
    mac_ua = mac_ver.replace(".", "_")
    return (
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X {mac_ua}) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        f"Version/{safari_version} Safari/605.1.15"
    )


def _read_uint32(data: bytes, offset: int, *, big_endian: bool = False) -> int:
    return struct.unpack_from(">I" if big_endian else "<I", data, offset)[0]


def _read_f64(data: bytes, offset: int, *, big_endian: bool = False) -> float:
    return struct.unpack_from(">d" if big_endian else "<d", data, offset)[0]


def _read_cstr(record: bytes, start: int) -> str:
    if start < 0 or start >= len(record):
        return ""
    end = record.find(b"\x00", start)
    if end == -1:
        end = len(record)
    return record[start:end].decode("utf-8", errors="ignore")


def _load_safari_cookie_records(raw: bytes) -> list[dict[str, object]]:
    if len(raw) < 8 or raw[:4] != b"cook":
        raise ValueError("Invalid Safari cookie file signature.")

    num_pages = _read_uint32(raw, 4, big_endian=True)
    cursor = 8
    page_sizes: list[int] = []
    for _ in range(num_pages):
        page_sizes.append(_read_uint32(raw, cursor, big_endian=True))
        cursor += 4

    pages_blob = raw[cursor:]
    page_cursor = 0
    out: list[dict[str, object]] = []

    for page_size in page_sizes:
        page = pages_blob[page_cursor : page_cursor + page_size]
        page_cursor += page_size
        if len(page) < 8 or page[:4] != b"\x00\x00\x01\x00":
            continue

        num_cookies = _read_uint32(page, 4)
        offsets: list[int] = []
        offsets_cursor = 8
        for _ in range(num_cookies):
            if offsets_cursor + 4 > len(page):
                break
            offsets.append(_read_uint32(page, offsets_cursor))
            offsets_cursor += 4

        for record_offset in offsets:
            if record_offset + 4 > len(page):
                continue
            record_size = _read_uint32(page, record_offset)
            if record_size <= 0 or record_offset + record_size > len(page):
                continue
            record = page[record_offset : record_offset + record_size]
            if len(record) < 56:
                continue

            flags = _read_uint32(record, 8)
            domain_off = _read_uint32(record, 16)
            name_off = _read_uint32(record, 20)
            path_off = _read_uint32(record, 24)
            value_off = _read_uint32(record, 28)
            exp_mac = _read_f64(record, 40)
            expires = int(978307200 + exp_mac)  # mac absolute epoch -> unix

            out.append(
                {
                    "secure": bool(flags & 0x1),
                    "domain": _read_cstr(record, domain_off),
                    "name": _read_cstr(record, name_off),
                    "path": _read_cstr(record, path_off),
                    "value": _read_cstr(record, value_off),
                    "expires": expires,
                }
            )
    return out
