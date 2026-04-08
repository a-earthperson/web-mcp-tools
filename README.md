# web-mcp-tools

[![Lint](https://img.shields.io/github/checks-status/a-earthperson/web-mcp-tools/main?checkName=Lint&label=lint)](https://github.com/a-earthperson/web-mcp-tools/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/github/checks-status/a-earthperson/web-mcp-tools/main?checkName=Tests&label=tests)](https://github.com/a-earthperson/web-mcp-tools/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/a-earthperson/web-mcp-tools/branch/main/graph/badge.svg)](https://codecov.io/gh/a-earthperson/web-mcp-tools)
[![CI](https://img.shields.io/github/checks-status/a-earthperson/web-mcp-tools/main?checkName=CI&label=CI)](https://github.com/a-earthperson/web-mcp-tools/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/web-mcp-tools)](https://pypi.org/project/web-mcp-tools/)
[![GHCR Tags](https://ghcr-badge.egpl.dev/a-earthperson/web-mcp-tools/tags?ignore=latest,sha256*&n=3&label=ghcr%20tags)](https://github.com/a-earthperson/web-mcp-tools/pkgs/container/web-mcp-tools)

Standalone MCP server and Python package for Firecrawl-backed web fetching with optional browser-cookie request headers.

## Install

```bash
uv sync --extra dev
```

## Configuration

- `FIRECRAWL_BASE_URL`: Firecrawl API base URL.
- `FIRECRAWL_API_KEY` or `FIRECRAWL_API_KEY_FILE`: Firecrawl API credential.
- `WEB_MCP_TOOLS_COOKIES_FROM_BROWSER`: Optional browser selector for authenticated fetches, for example `safari` or `safari:/path/to/Cookies.binarycookies`.
- `WEB_MCP_TOOLS_COOKIES_MODE`: `off`, `best_effort`, or `required`.
- `WEB_MCP_TOOLS_HOST`: HTTP bind host for MCP HTTP transports.
- `WEB_MCP_TOOLS_PORT`: HTTP bind port for MCP HTTP transports.
- `WEB_MCP_TOOLS_STREAMABLE_HTTP_PATH`: Streamable HTTP endpoint path. Defaults to `/mcp`.

## Run

Run over stdio:

```bash
uv run web-mcp-tools mcp
```

Run over Streamable HTTP:

```bash
uv run web-mcp-tools mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

The HTTP server exposes health probes at `/health` and `/healthz`, and the default Streamable HTTP MCP endpoint at `/mcp`.

Compatibility health-only server:

```bash
uv run web-mcp-tools serve --host 127.0.0.1 --port 8000
```

## Build

```bash
uv build
```

## Test

```bash
uv run pytest
```
