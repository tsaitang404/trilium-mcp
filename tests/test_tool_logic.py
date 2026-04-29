"""Tests for tool logic with mocked ETAPI client."""

from unittest.mock import MagicMock
import pytest

from trilium_mcp.models import AppInfo, NoteInfo, SearchResult, NoteContent, TodoResult


@pytest.fixture
def mock_ea():
    ea = MagicMock()
    return ea


@pytest.fixture
def mock_ctx(mock_ea):
    """Build a mock Context with lifespan context containing a mock ETAPI."""
    from mcp.server.fastmcp import Context
    from mcp.server.session import ServerSession
    from dataclasses import dataclass

    @dataclass
    class AppContext:
        ea: object

    class MockRequestContext:
        lifespan_context = AppContext(ea=mock_ea)

    ctx = MagicMock(spec=Context)
    ctx.request_context = MockRequestContext()
    return ctx


class TestAppInfo:
    def test_ok(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_app_info

        mock_ea.app_info.return_value = {
            "appVersion": "0.103.0",
            "dbVersion": 251,
            "syncVersion": 5,
        }
        result = tool_app_info(ctx=mock_ctx)
        assert isinstance(result, AppInfo)
        assert result.app_version == "0.103.0"
        assert result.db_version == 251

    def test_empty_server(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_app_info

        mock_ea.app_info.return_value = {}
        result = tool_app_info(ctx=mock_ctx)
        assert result.app_version == ""


class TestSearchNotes:
    def test_basic(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_search_notes

        mock_ea.search_note.return_value = {
            "results": [
                {"noteId": "n1", "title": "Python", "type": "text"},
                {"noteId": "n2", "title": "JavaScript", "type": "code"},
            ]
        }
        result = tool_search_notes(search="python", ctx=mock_ctx)
        assert isinstance(result, SearchResult)
        assert len(result.results) == 2
        assert result.results[0].note_id == "n1"
        assert result.results[1].type == "code"

    def test_empty(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_search_notes

        mock_ea.search_note.return_value = {"results": []}
        result = tool_search_notes(search="zzz", ctx=mock_ctx)
        assert len(result.results) == 0

    def test_with_params(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_search_notes

        mock_ea.search_note.return_value = {"results": []}
        tool_search_notes(
            search="test",
            ctx=mock_ctx,
            ancestor_note_id="root",
            fast_search=False,
            limit=10,
        )
        _, kwargs = mock_ea.search_note.call_args
        assert kwargs["ancestorNoteId"] == "root"
        assert kwargs["fastSearch"] is False
        assert kwargs["limit"] == 10


class TestCreateNote:
    def test_create(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_create_note

        mock_ea.create_note.return_value = {
            "note": {
                "noteId": "n1",
                "title": "Hello",
                "type": "text",
            }
        }
        result = tool_create_note(
            parent_note_id="root",
            title="Hello",
            type="text",
            content="<p>World</p>",
            ctx=mock_ctx,
        )
        assert isinstance(result, NoteInfo)
        assert result.note_id == "n1"
        assert result.title == "Hello"

    def test_with_custom_note_id(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_create_note

        mock_ea.create_note.return_value = {"note": {"noteId": "myid", "title": "X"}}
        tool_create_note(
            parent_note_id="root",
            title="X",
            type="text",
            content="c",
            note_id="myid",
            ctx=mock_ctx,
        )
        args, kwargs = mock_ea.create_note.call_args
        assert kwargs["noteId"] == "myid"


class TestGetNote:
    def test_get(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_get_note

        mock_ea.get_note.return_value = {
            "noteId": "n1",
            "title": "My Note",
            "type": "text",
            "mime": "text/html",
        }
        result = tool_get_note(note_id="n1", ctx=mock_ctx)
        assert isinstance(result, NoteInfo)
        assert result.note_id == "n1"
        assert result.title == "My Note"


class TestGetNoteContent:
    def test_get(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_get_note_content

        mock_ea.get_note_content.return_value = "<p>Hello World</p>"
        result = tool_get_note_content(note_id="n1", ctx=mock_ctx)
        assert isinstance(result, NoteContent)
        assert result.content == "<p>Hello World</p>"


class TestUpdateNoteContent:
    def test_ok(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_update_note_content

        mock_ea.update_note_content.return_value = True
        result = tool_update_note_content(note_id="n1", content="new", ctx=mock_ctx)
        assert isinstance(result, TodoResult)
        assert result.ok is True

    def test_fail(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_update_note_content

        mock_ea.update_note_content.return_value = False
        result = tool_update_note_content(note_id="n1", content="new", ctx=mock_ctx)
        assert result.ok is False


class TestDeleteNote:
    def test_ok(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_delete_note

        mock_ea.delete_note.return_value = None  # no exception
        result = tool_delete_note(note_id="n1", ctx=mock_ctx)
        assert result.ok is True
        mock_ea.delete_note.assert_called_once_with("n1")

    def test_fail(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_delete_note

        mock_ea.delete_note.side_effect = Exception("not found")
        result = tool_delete_note(note_id="bad", ctx=mock_ctx)
        assert result.ok is False
        assert "not found" in result.message


class TestCreateBranch:
    def test_clone(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_create_branch

        mock_ea.create_branch.return_value = {
            "branchId": "p_n",
            "noteId": "n",
            "parentNoteId": "p",
            "prefix": None,
            "notePosition": 5,
            "isExpanded": False,
            "utcDateModified": "2026-01-01T00:00:00Z",
        }
        result = tool_create_branch(
            note_id="n", parent_note_id="p", ctx=mock_ctx
        )
        assert result.branch_id == "p_n"
        assert result.note_position == 5


class TestTodoCrud:
    def test_add(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_add_todo

        mock_ea.add_todo.return_value = True
        result = tool_add_todo(description="buy milk", ctx=mock_ctx)
        assert result.ok is True

    def test_check(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_todo_check

        mock_ea.todo_check.return_value = True
        result = tool_todo_check(index=0, ctx=mock_ctx, checked=True)
        assert result.ok is True

    def test_update(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_update_todo

        mock_ea.update_todo.return_value = True
        result = tool_update_todo(index=0, description="new desc", ctx=mock_ctx)
        assert result.ok is True

    def test_delete(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_delete_todo

        mock_ea.delete_todo.return_value = True
        result = tool_delete_todo(index=0, ctx=mock_ctx)
        assert result.ok is True


class TestExportNote:
    def test_ok(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_export_note

        mock_ea.export_note.return_value = None
        result = tool_export_note(
            note_id="n1", format="md", save_path="/tmp/test.zip", ctx=mock_ctx
        )
        assert result.success is True
        assert "test.zip" in result.message

    def test_fail(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_export_note

        mock_ea.export_note.side_effect = PermissionError("denied")
        result = tool_export_note(
            note_id="n1", format="md", save_path="/tmp/test.zip", ctx=mock_ctx
        )
        assert result.success is False


class TestSetDayNote:
    def test_ok(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_set_day_note

        mock_ea.set_day_note.return_value = None
        result = tool_set_day_note(date="2026-04-29", content="<p>test</p>", ctx=mock_ctx)
        assert result.ok is True

    def test_fail(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_set_day_note

        mock_ea.set_day_note.side_effect = Exception("error")
        result = tool_set_day_note(date="2026-04-29", content="<p>test</p>", ctx=mock_ctx)
        assert result.ok is False


class TestPatchNote:
    def test_rename(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_patch_note

        mock_ea.patch_note.return_value = {
            "note": {"noteId": "n1", "title": "New Title"}
        }
        result = tool_patch_note(note_id="n1", title="New Title", ctx=mock_ctx)
        assert result.note_id == "n1"
        assert result.title == "New Title"


class TestBeautifyNote:
    def test_ok(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_beautify_note

        mock_ea.beautify_note.return_value = True
        result = tool_beautify_note(note_id="n1", ctx=mock_ctx)
        assert result.ok is True

    def test_fail(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_beautify_note

        mock_ea.beautify_note.return_value = False
        result = tool_beautify_note(note_id="n1", ctx=mock_ctx)
        assert result.ok is False


class TestSaveRevision:
    def test_ok(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_save_revision

        mock_ea.save_revision.return_value = None
        result = tool_save_revision(note_id="n1", ctx=mock_ctx)
        assert result.ok is True

    def test_fail(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_save_revision

        mock_ea.save_revision.side_effect = Exception("error")
        result = tool_save_revision(note_id="n1", ctx=mock_ctx)
        assert result.ok is False


class TestGetBackup:
    def test_ok(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_get_backup

        mock_ea.backup.return_value = None
        result = tool_get_backup(name="test_backup", ctx=mock_ctx)
        assert result.ok is True

    def test_fail(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_get_backup

        mock_ea.backup.side_effect = Exception("disk full")
        result = tool_get_backup(name="test_backup", ctx=mock_ctx)
        assert result.ok is False


class TestMoveYesterdayTodo:
    def test_ok(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_move_yesterday_todo

        mock_ea.move_yesterday_unfinished_todo_to_today.return_value = None
        result = tool_move_yesterday_todo(ctx=mock_ctx)
        assert result.ok is True

    def test_fail(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_move_yesterday_todo

        mock_ea.move_yesterday_unfinished_todo_to_today.side_effect = Exception("error")
        result = tool_move_yesterday_todo(ctx=mock_ctx)
        assert result.ok is False


class TestImportNote:
    def test_ok(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_import_note

        mock_ea.import_note.return_value = None
        result = tool_import_note(note_id="n1", file_path="/tmp/test.zip", ctx=mock_ctx)
        assert result.ok is True

    def test_fail(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_import_note

        mock_ea.import_note.side_effect = FileNotFoundError("not found")
        result = tool_import_note(note_id="n1", file_path="/tmp/test.zip", ctx=mock_ctx)
        assert result.ok is False


class TestCreateAttribute:
    def test_label(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_create_attribute

        mock_ea.create_attribute.return_value = {
            "attributeId": "a1",
            "noteId": "n1",
            "type": "label",
            "name": "tag1",
            "value": "val1",
            "isInheritable": False,
        }
        result = tool_create_attribute(
            note_id="n1", type="label", name="tag1", value="val1", ctx=mock_ctx
        )
        assert result.attribute_id == "a1"
        assert result.name == "tag1"


class TestCreateImageNote:
    def test_create(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_create_image_note

        mock_ea.create_image_note.return_value = {
            "note": {"noteId": "img1", "title": "Photo", "type": "image"}
        }
        result = tool_create_image_note(
            parent_note_id="root",
            title="Photo",
            image_file="/tmp/photo.png",
            ctx=mock_ctx,
        )
        assert result.note_id == "img1"
        assert result.type == "image"


class TestSearchByTitle:
    def test_search(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_search_by_title

        mock_ea.search_note.return_value = {
            "results": [{"noteId": "n1", "title": "Exact Title"}]
        }
        result = tool_search_by_title(title="Exact Title", ctx=mock_ctx)
        assert len(result) == 1
        assert result[0].title == "Exact Title"


class TestGetAttachments:
    def test_list(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_get_attachments

        mock_ea.get_attachments.return_value = [
            {"attachmentId": "a1", "title": "img.png", "role": "image"}
        ]
        result = tool_get_attachments(note_id="n1", ctx=mock_ctx)
        assert len(result) == 1
        assert result[0]["attachmentId"] == "a1"

    def test_empty(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_get_attachments

        mock_ea.get_attachments.return_value = []
        result = tool_get_attachments(note_id="n1", ctx=mock_ctx)
        assert result == []

    def test_none(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_get_attachments

        mock_ea.get_attachments.return_value = None
        result = tool_get_attachments(note_id="n1", ctx=mock_ctx)
        assert result == []


class TestTraverse:
    def test_dfs(self, mock_ea, mock_ctx):
        from trilium_mcp.main import tool_traverse_note_tree

        mock_ea.traverse_note_tree.return_value = [
            {"noteId": "n1", "title": "Root", "type": "text", "content": "abc"},
            {"noteId": "n2", "title": "Child", "type": "code", "content": "print(1)"},
        ]
        result = tool_traverse_note_tree(note_id="n1", ctx=mock_ctx)
        assert len(result) == 2
        assert result[0].note_id == "n1"
        assert result[0].content == "abc"
