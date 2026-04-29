"""Tests for lifespan and server initialization."""

import os
import sys

import pytest


@pytest.mark.asyncio
async def test_lifespan_requires_token():
    """Lifespan raises RuntimeError when TRILIUM_TOKEN is missing."""
    from trilium_mcp.main import lifespan, mcp

    token = os.environ.pop("TRILIUM_TOKEN", None)
    url = os.environ.pop("TRILIUM_URL", None)

    try:
        with pytest.raises(RuntimeError, match="TRILIUM_TOKEN"):
            async with lifespan(mcp) as ctx:
                pass
    finally:
        if token is not None:
            os.environ["TRILIUM_TOKEN"] = token
        if url is not None:
            os.environ["TRILIUM_URL"] = url


def test_main_transport_stdio(monkeypatch):
    """main() function starts with stdio transport."""
    from trilium_mcp.main import mcp

    original_run = mcp.run
    captured = []

    def mock_run(*args, **kwargs):
        captured.append((args, kwargs))
        raise SystemExit(0)

    mcp.run = mock_run
    monkeypatch.setenv("TRILIUM_MCP_TRANSPORT", "stdio")
    monkeypatch.setenv("TRILIUM_URL", "http://localhost:8080")
    monkeypatch.setenv("TRILIUM_TOKEN", "test")

    from trilium_mcp.main import main
    with pytest.raises(SystemExit):
        main()
    mcp.run = original_run


def test_main_transport_sse(monkeypatch):
    """main() function starts with sse transport."""
    from trilium_mcp.main import mcp

    original_run = mcp.run
    captured = []

    def mock_run(*args, **kwargs):
        captured.append(kwargs)
        raise SystemExit(0)

    mcp.run = mock_run
    monkeypatch.setenv("TRILIUM_MCP_TRANSPORT", "sse")
    monkeypatch.setenv("TRILIUM_URL", "http://localhost:8080")
    monkeypatch.setenv("TRILIUM_TOKEN", "test")

    from trilium_mcp.main import main
    with pytest.raises(SystemExit):
        main()
    mcp.run = original_run
    assert len(captured) == 1
    assert captured[0]["transport"] == "sse"


def test_main_transport_http(monkeypatch):
    from trilium_mcp.main import mcp

    original_run = mcp.run
    captured = []

    def mock_run(*args, **kwargs):
        captured.append(kwargs)
        raise SystemExit(0)

    mcp.run = mock_run
    monkeypatch.setenv("TRILIUM_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("TRILIUM_URL", "http://localhost:8080")
    monkeypatch.setenv("TRILIUM_TOKEN", "test")

    from trilium_mcp.main import main
    with pytest.raises(SystemExit):
        main()
    mcp.run = original_run
    assert captured[0]["transport"] == "streamable-http"
