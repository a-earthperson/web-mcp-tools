"""Environment variable helpers for standalone package configuration."""

from __future__ import annotations

import os
from pathlib import Path


def _read_env_file(name: str) -> str | None:
    path_raw = os.getenv(f"{name}_FILE")
    if path_raw is None:
        return None
    path_value = path_raw.strip()
    if not path_value:
        return None
    path = Path(path_value).expanduser()
    try:
        contents = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(
            f"Failed to read environment file {name}_FILE={path}: {exc}"
        ) from exc
    value = contents.strip()
    if value:
        return value
    return None


def get_env_value(*names: str, required: bool = False, default: str = "") -> str:
    for name in names:
        raw = os.getenv(name)
        if raw is None:
            continue
        value = raw.strip()
        if value:
            return value
    if required:
        raise ValueError(f"Required environment variable {names} not set.")
    return default


def get_secret_env_value(*names: str, required: bool = False, default: str = "") -> str:
    """Resolve a secret from `NAME` or `NAME_FILE` environment variables."""

    for name in names:
        raw = os.getenv(name)
        if raw is not None:
            value = raw.strip()
            if value:
                return value
        file_value = _read_env_file(name)
        if file_value:
            return file_value
    if required:
        raise ValueError(f"Required secret environment variable {names} not set.")
    return default


def get_env_int(name: str, *, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer.") from exc
