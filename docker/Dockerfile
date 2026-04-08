# syntax=docker/dockerfile:1.7
############################
# Builder: resolve/install deps into a venv
############################
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN python -m venv "${VIRTUAL_ENV}" \
 && pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY README.md LICENSE ./
RUN uv sync --frozen

############################
# Runtime: copy venv only
############################
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/src

RUN addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/src /app/src

WORKDIR /app

RUN chown -R app:app /app

USER app

ENV WEB_MCP_TOOLS_HOST=0.0.0.0 \
    WEB_MCP_TOOLS_PORT=8000 \
    WEB_MCP_TOOLS_STREAMABLE_HTTP_PATH=/mcp

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"

CMD ["web-mcp-tools", "mcp", "--transport", "streamable-http"]
