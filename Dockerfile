FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml .
COPY src/ src/

RUN uv pip install --system --no-cache .

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/trilium-mcp /usr/local/bin/trilium-mcp

EXPOSE 8000

ENV TRILIUM_MCP_TRANSPORT=streamable-http

ENTRYPOINT ["trilium-mcp"]
