"""Pydantic-compatible HTTP URL normalization shared by web tools."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import urlsplit, urlunsplit

from pydantic import AfterValidator, AnyHttpUrl, BeforeValidator, TypeAdapter

_http_url_adapter = TypeAdapter(AnyHttpUrl)


def _normalize_http_url(url: str) -> str:
    """Canonicalize scheme/netloc casing and trim trailing slash from path."""

    parsed = urlsplit(url.strip())
    path = parsed.path.rstrip("/")
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            parsed.query,
            "",
        )
    )


Url = Annotated[
    str,
    BeforeValidator(lambda value: str(_http_url_adapter.validate_python(value))),
    AfterValidator(_normalize_http_url),
]
