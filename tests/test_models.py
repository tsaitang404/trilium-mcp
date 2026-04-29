"""Tests for Pydantic models."""

import pytest
from trilium_mcp.models import (
    AppInfo, NoteInfo, SearchResult, BranchInfo,
    AttributeInfo, NoteContent, NoteTreeItem,
    TodoResult, ExportInfo,
)


class TestAppInfo:
    def test_minimal(self):
        info = AppInfo(app_version="1.0", db_version=1, sync_version=1)
        assert info.app_version == "1.0"
        assert info.db_version == 1
        assert info.sync_version == 1

    def test_defaults(self):
        info = AppInfo(app_version="2.0", db_version=2, sync_version=2)
        assert info.build_date == ""
        assert info.build_revision == ""
        assert info.utc_date_time == ""


class TestNoteInfo:
    def test_minimal(self):
        note = NoteInfo(note_id="abc123")
        assert note.note_id == "abc123"
        assert note.title == ""
        assert note.type == "text"

    def test_with_parents_and_children(self):
        note = NoteInfo(
            note_id="x1",
            title="Test",
            type="code",
            mime="text/javascript",
            parent_note_ids=["root"],
            child_note_ids=["c1", "c2"],
        )
        assert note.parent_note_ids == ["root"]
        assert note.child_note_ids == ["c1", "c2"]

    def test_protected(self):
        note = NoteInfo(note_id="x1", is_protected=True)
        assert note.is_protected is True

    def test_list_defaults(self):
        note = NoteInfo(note_id="x1")
        assert note.parent_note_ids == []
        assert note.child_note_ids == []


class TestSearchResult:
    def test_empty(self):
        res = SearchResult()
        assert res.results == []

    def test_with_results(self):
        res = SearchResult(results=[NoteInfo(note_id="a"), NoteInfo(note_id="b")])
        assert len(res.results) == 2

    def test_list_default(self):
        res = SearchResult()
        assert res.results == []


class TestBranchInfo:
    def test_minimal(self):
        b = BranchInfo(
            branch_id="p_n",
            note_id="n",
            parent_note_id="p",
        )
        assert b.branch_id == "p_n"
        assert b.note_id == "n"
        assert b.parent_note_id == "p"

    def test_with_prefix(self):
        b = BranchInfo(
            branch_id="p_n",
            note_id="n",
            parent_note_id="p",
            note_position=5,
            prefix="docs",
        )
        assert b.prefix == "docs"
        assert b.note_position == 5


class TestAttributeInfo:
    def test_minimal(self):
        a = AttributeInfo(
            attribute_id="attr1",
            note_id="n1",
            type="label",
            name="tag1",
        )
        assert a.attribute_id == "attr1"

    def test_inheritable(self):
        a = AttributeInfo(
            attribute_id="attr1",
            note_id="n1",
            type="label",
            name="tag1",
            is_inheritable=True,
        )
        assert a.is_inheritable is True


class TestNoteContent:
    def test_content(self):
        nc = NoteContent(note_id="n1", content="<p>hello</p>")
        assert nc.content == "<p>hello</p>"


class TestNoteTreeItem:
    def test_minimal(self):
        item = NoteTreeItem(note_id="n1")
        assert item.title == ""
        assert item.type == "text"

    def test_full(self):
        item = NoteTreeItem(
            note_id="n1",
            title="Test",
            type="code",
            content="print(1)",
        )
        assert item.content == "print(1)"


class TestTodoResult:
    def test_ok(self):
        r = TodoResult(ok=True, message="done")
        assert r.ok is True

    def test_fail(self):
        r = TodoResult(ok=False, message="failed: reason")
        assert r.ok is False


class TestExportInfo:
    def test_success(self):
        e = ExportInfo(note_id="n1", format="md", success=True)
        assert e.success is True

    def test_failure(self):
        e = ExportInfo(note_id="n1", format="html", success=False, message="error")
        assert e.success is False
