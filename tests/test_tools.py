"""Tests for tool registration and server setup."""

import os
import subprocess
import sys

import pytest


def test_all_tools_registered():
    """Verify all expected tools are registered."""
    from trilium_mcp.main import mcp

    tool_names = {t.name for t in mcp._tool_manager._tools.values()}

    expected = {
        "app_info",
        "search_notes",
        "search_by_title",
        "get_note",
        "get_note_content",
        "create_note",
        "create_image_note",
        "update_note_content",
        "patch_note",
        "delete_note",
        "create_branch",
        "create_attribute",
        "export_note",
        "import_note",
        "get_day_note",
        "set_day_note",
        "add_todo",
        "todo_check",
        "update_todo",
        "delete_todo",
        "move_yesterday_unfinished_todo",
        "beautify_note",
        "traverse_note_tree",
        "get_attachments",
        "save_revision",
        "get_backup",
    }

    missing = expected - tool_names
    extra = tool_names - expected
    assert not missing, f"Missing tools: {missing}"
    assert not extra, f"Unexpected tools: {extra}"


def test_tool_has_descriptions():
    """Every tool should have a description."""
    from trilium_mcp.main import mcp

    for t in mcp._tool_manager._tools.values():
        assert t.description, f"Tool '{t.name}' is missing a description"


def test_console_entrypoint():
    """The installed console script should exist."""
    result = subprocess.run(
        [sys.executable, "-m", "trilium_mcp.main"],
        env={"TRILIUM_URL": "http://localhost:8080", "TRILIUM_TOKEN": "test"},
        capture_output=True,
        timeout=5,
    )
    # It will either fail at startup (token invalid) or stdio setup, but the import should work
    assert "ModuleNotFoundError" not in result.stderr.decode()
    assert "Error" not in result.stderr.decode()
