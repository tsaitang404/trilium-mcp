"""Trilium Notes MCP server.

Wrap Trilium ETAPI (via trilium-py) as a standard MCP service.
All tool functions use the ETAPI client injected through lifespan context.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import os

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from trilium_py.client import ETAPI

from trilium_mcp.models import (
    AppInfo,
    AttributeInfo,
    BranchInfo,
    ExportInfo,
    NoteContent,
    NoteInfo,
    NoteTreeItem,
    SearchResult,
    TodoResult,
)


# ── lifespan: init ETAPI client once ──────────────────────────────────

@dataclass
class AppContext:
    ea: ETAPI


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    url = os.environ.get("TRILIUM_URL", "http://localhost:8080")
    token = os.environ.get("TRILIUM_TOKEN")
    if not token:
        raise RuntimeError("TRILIUM_TOKEN environment variable is required")
    ea = ETAPI(url, token)
    try:
        yield AppContext(ea=ea)
    finally:
        pass  # ETAPI has no explicit close


mcp = FastMCP("trilium-mcp", json_response=True, lifespan=lifespan, host="0.0.0.0", port=8000)


# ── helpers ───────────────────────────────────────────────────────────

def _check_required(value: str | None, name: str) -> str:
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _scrub_note(raw: dict) -> NoteInfo:
    """Convert raw ETAPI note dict to clean NoteInfo."""
    return NoteInfo(
        note_id=raw.get("noteId", ""),
        title=raw.get("title", ""),
        type=raw.get("type", "text"),
        mime=raw.get("mime", "text/html"),
        is_protected=raw.get("isProtected", False),
        blob_id=raw.get("blobId"),
        parent_note_ids=raw.get("parentNoteIds") or [],
        child_note_ids=raw.get("childNoteIds") or [],
    )


# ── tools ─────────────────────────────────────────────────────────────

@mcp.tool(name="app_info")
def tool_app_info(ctx: Context[ServerSession, AppContext]) -> AppInfo:
    """获取 Trilium 服务器信息（版本、数据库版本等）。"""
    raw = ctx.request_context.lifespan_context.ea.app_info()
    return AppInfo(
        app_version=raw.get("appVersion", ""),
        db_version=raw.get("dbVersion", 0),
        sync_version=raw.get("syncVersion", 0),
        build_date=raw.get("buildDate", ""),
        build_revision=raw.get("buildRevision", ""),
        utc_date_time=raw.get("utcDateTime", ""),
    )


@mcp.tool(name="search_notes")
def tool_search_notes(
    search: str,
    ctx: Context[ServerSession, AppContext],
    ancestor_note_id: str | None = None,
    fast_search: bool = True,
    include_archived: bool = False,
    order_by: list[str] | None = None,
    limit: int | None = None,
    debug: bool = False,
) -> SearchResult:
    """搜索笔记。

    支持按标题搜索（默认）或使用 note.title 等字段进行正则搜索。
    若需要正则匹配，设置 fast_search=False 并调整 search 表达式。
    """
    ea = ctx.request_context.lifespan_context.ea
    kwargs = {
        "fastSearch": fast_search,
        "includeArchivedNotes": include_archived,
    }
    if ancestor_note_id:
        kwargs["ancestorNoteId"] = ancestor_note_id
    if order_by:
        kwargs["orderBy"] = order_by
    if limit is not None:
        kwargs["limit"] = limit
    if debug:
        kwargs["debug"] = True

    raw = ea.search_note(search, **kwargs)
    return SearchResult(
        results=[_scrub_note(r) for r in raw.get("results", [])],
    )


@mcp.tool(name="get_note")
def tool_get_note(
    note_id: str, ctx: Context[ServerSession, AppContext]
) -> NoteInfo:
    """通过 ID 获取笔记元数据（不含内容）。"""
    ea = ctx.request_context.lifespan_context.ea
    raw = ea.get_note(note_id)
    return _scrub_note(raw)


@mcp.tool(name="get_note_content")
def tool_get_note_content(
    note_id: str, ctx: Context[ServerSession, AppContext]
) -> NoteContent:
    """获取笔记的 HTML 内容。"""
    ea = ctx.request_context.lifespan_context.ea
    content = ea.get_note_content(note_id)
    return NoteContent(note_id=note_id, content=content)


@mcp.tool(name="create_note")
def tool_create_note(
    parent_note_id: str,
    title: str,
    type: str,
    content: str,
    ctx: Context[ServerSession, AppContext],
    note_id: str | None = None,
    mime: str | None = None,
) -> NoteInfo:
    """创建笔记。

    Args:
        parent_note_id: 父笔记 ID，使用 "root" 表示根节点
        title: 笔记标题
        type: 笔记类型（text, code, file, image, search, relationMap, render, canvas）
        content: 笔记内容（text 类型为 HTML）
        note_id: 可选的自定义 noteId
        mime: MIME 类型，text 类型默认 text/html
    """
    ea = ctx.request_context.lifespan_context.ea
    kwargs = {}
    if note_id:
        kwargs["noteId"] = note_id
    if mime:
        kwargs["mime"] = mime
    raw = ea.create_note(
        parentNoteId=parent_note_id, title=title, type=type, content=content, **kwargs
    )
    return _scrub_note(raw.get("note", raw))


@mcp.tool(name="create_image_note")
def tool_create_image_note(
    parent_note_id: str,
    title: str,
    image_file: str,
    ctx: Context[ServerSession, AppContext],
) -> NoteInfo:
    """从本地图片文件创建图片笔记。

    Args:
        parent_note_id: 父笔记 ID
        title: 笔记标题
        image_file: 本地图片文件路径
    """
    ea = ctx.request_context.lifespan_context.ea
    raw = ea.create_image_note(
        parentNoteId=parent_note_id, title=title, image_file=image_file
    )
    return _scrub_note(raw.get("note", raw))


@mcp.tool(name="update_note_content")
def tool_update_note_content(
    note_id: str, content: str, ctx: Context[ServerSession, AppContext]
) -> TodoResult:
    """更新笔记内容。"""
    ea = ctx.request_context.lifespan_context.ea
    ok = ea.update_note_content(note_id, content)
    return TodoResult(ok=ok, message="updated" if ok else "failed")


@mcp.tool(name="patch_note")
def tool_patch_note(
    note_id: str,
    ctx: Context[ServerSession, AppContext],
    title: str | None = None,
) -> NoteInfo:
    """修改笔记标题（后续可扩展其他属性）。"""
    ea = ctx.request_context.lifespan_context.ea
    raw = ea.patch_note(noteId=note_id, title=title)
    return _scrub_note(raw.get("note", raw))


@mcp.tool(name="delete_note")
def tool_delete_note(
    note_id: str, ctx: Context[ServerSession, AppContext]
) -> TodoResult:
    """删除笔记（不可恢复，谨慎使用）。"""
    ea = ctx.request_context.lifespan_context.ea
    try:
        ea.delete_note(note_id)
        return TodoResult(ok=True, message=f"deleted {note_id}")
    except Exception as e:
        return TodoResult(ok=False, message=str(e))


@mcp.tool(name="create_branch")
def tool_create_branch(
    note_id: str,
    parent_note_id: str,
    ctx: Context[ServerSession, AppContext],
    prefix: str = "",
    note_position: int = 0,
) -> BranchInfo:
    """克隆笔记到另一父节点下（创建分支/克隆）。

    Args:
        note_id: 要克隆的笔记 ID
        parent_note_id: 目标父笔记 ID
        prefix: 分支前缀
        note_position: 子笔记中的排序位置
    """
    ea = ctx.request_context.lifespan_context.ea
    raw = ea.create_branch(
        noteId=note_id,
        parentNoteId=parent_note_id,
        prefix=prefix,
        notePosition=note_position,
    )
    return BranchInfo(
        branch_id=raw.get("branchId", ""),
        note_id=raw.get("noteId", ""),
        parent_note_id=raw.get("parentNoteId", ""),
        prefix=raw.get("prefix"),
        note_position=raw.get("notePosition", 0),
        is_expanded=raw.get("isExpanded", False),
        utc_date_modified=raw.get("utcDateModified", ""),
    )


@mcp.tool(name="create_attribute")
def tool_create_attribute(
    note_id: str,
    type: str,
    name: str,
    value: str,
    ctx: Context[ServerSession, AppContext],
    is_inheritable: bool = False,
) -> AttributeInfo:
    """为笔记创建属性（标签 label 或关系 relation）。

    Args:
        note_id: 目标笔记 ID
        type: 属性类型，"label" 或 "relation"
        name: 属性名称
        value: 属性值
        is_inheritable: 是否被子笔记继承
    """
    ea = ctx.request_context.lifespan_context.ea
    raw = ea.create_attribute(
        noteId=note_id,
        type=type,
        name=name,
        value=value,
        isInheritable=is_inheritable,
    )
    return AttributeInfo(
        attribute_id=raw.get("attributeId", ""),
        note_id=raw.get("noteId", ""),
        type=raw.get("type", type),
        name=raw.get("name", name),
        value=raw.get("value", value),
        is_inheritable=raw.get("isInheritable", is_inheritable),
    )


@mcp.tool(name="export_note")
def tool_export_note(
    note_id: str,
    format: str,
    save_path: str,
    ctx: Context[ServerSession, AppContext],
) -> ExportInfo:
    """导出笔记为文件。

    Args:
        note_id: 笔记 ID，使用 "root" 导出全部
        format: 导出格式，"html" 或 "md"/"markdown"
        save_path: 输出文件路径（.zip）
    """
    ea = ctx.request_context.lifespan_context.ea
    try:
        ea.export_note(noteId=note_id, format=format, save_path=save_path)
        return ExportInfo(
            note_id=note_id, format=format, success=True, message=f"exported to {save_path}"
        )
    except Exception as e:
        return ExportInfo(note_id=note_id, format=format, success=False, message=str(e))


@mcp.tool(name="import_note")
def tool_import_note(
    note_id: str,
    file_path: str,
    ctx: Context[ServerSession, AppContext],
) -> TodoResult:
    """从 zip 文件导入笔记到指定节点下。

    Args:
        note_id: 目标父笔记 ID
        file_path: 要导入的 zip 文件路径
    """
    ea = ctx.request_context.lifespan_context.ea
    try:
        ea.import_note(noteId=note_id, file_path=file_path)
        return TodoResult(ok=True, message=f"imported from {file_path}")
    except Exception as e:
        return TodoResult(ok=False, message=str(e))


@mcp.tool(name="get_day_note")
def tool_get_day_note(
    date: str, ctx: Context[ServerSession, AppContext]
) -> NoteContent:
    """获取指定日期的日记内容。

    Args:
        date: 日期字符串，格式为 "%Y-%m-%d"，例如 "2026-04-29"
    """
    ea = ctx.request_context.lifespan_context.ea
    content = ea.get_day_note(date)
    return NoteContent(note_id=f"day:{date}", content=content)


@mcp.tool(name="set_day_note")
def tool_set_day_note(
    date: str, content: str, ctx: Context[ServerSession, AppContext]
) -> TodoResult:
    """设置/更新指定日期的日记内容。

    Args:
        date: 日期字符串，格式为 "%Y-%m-%d"
        content: HTML 笔记内容
    """
    ea = ctx.request_context.lifespan_context.ea
    try:
        ea.set_day_note(date, content)
        return TodoResult(ok=True, message=f"day note {date} updated")
    except Exception as e:
        return TodoResult(ok=False, message=str(e))


@mcp.tool(name="add_todo")
def tool_add_todo(
    description: str, ctx: Context[ServerSession, AppContext], date: str | None = None
) -> TodoResult:
    """在今天（或指定日期）的日记中添加 TODO 项。

    Args:
        description: TODO 描述
        date: 可选日期，默认今天，格式 "%Y-%m-%d"
    """
    ea = ctx.request_context.lifespan_context.ea
    ok = ea.add_todo(description, date=date)
    return TodoResult(ok=ok, message="added" if ok else "failed")


@mcp.tool(name="todo_check")
def tool_todo_check(
    index: int, ctx: Context[ServerSession, AppContext], checked: bool = True
) -> TodoResult:
    """勾选或取消勾选 TODO 项。

    Args:
        index: TODO 索引（从 0 开始）
        checked: True 表示勾选，False 表示取消勾选
    """
    ea = ctx.request_context.lifespan_context.ea
    ok = ea.todo_check(index, check=checked)
    return TodoResult(ok=ok, message="updated" if ok else "failed")


@mcp.tool(name="update_todo")
def tool_update_todo(
    index: int, description: str, ctx: Context[ServerSession, AppContext]
) -> TodoResult:
    """更新指定 TODO 项的描述。

    Args:
        index: TODO 索引（从 0 开始）
        description: 新的 TODO 描述
    """
    ea = ctx.request_context.lifespan_context.ea
    ok = ea.update_todo(index, description)
    return TodoResult(ok=ok, message="updated" if ok else "failed")


@mcp.tool(name="delete_todo")
def tool_delete_todo(
    index: int, ctx: Context[ServerSession, AppContext]
) -> TodoResult:
    """删除指定的 TODO 项。

    Args:
        index: TODO 索引（从 0 开始）
    """
    ea = ctx.request_context.lifespan_context.ea
    ok = ea.delete_todo(index)
    return TodoResult(ok=ok, message="deleted" if ok else "failed")


@mcp.tool(name="move_yesterday_unfinished_todo")
def tool_move_yesterday_todo(ctx: Context[ServerSession, AppContext]) -> TodoResult:
    """将昨天未完成的 TODO 迁移到今天。"""
    ea = ctx.request_context.lifespan_context.ea
    try:
        ea.move_yesterday_unfinished_todo_to_today()
        return TodoResult(ok=True, message="moved")
    except Exception as e:
        return TodoResult(ok=False, message=str(e))


@mcp.tool(name="beautify_note")
def tool_beautify_note(
    note_id: str, ctx: Context[ServerSession, AppContext]
) -> TodoResult:
    """美化笔记内容（自动清理多余空行、规范化排版）。"""
    ea = ctx.request_context.lifespan_context.ea
    ok = ea.beautify_note(note_id)
    return TodoResult(ok=ok, message="beautified" if ok else "failed")


@mcp.tool(name="traverse_note_tree")
def tool_traverse_note_tree(
    note_id: str,
    ctx: Context[ServerSession, AppContext],
    depth: int = 3,
    limit: int = 100,
    method: str = "dfs",
) -> list[NoteTreeItem]:
    """遍历笔记树，收集当前笔记及其后代的标题和内容。

    Args:
        note_id: 起始笔记 ID
        depth: 最大遍历深度
        limit: 最大返回条目数
        method: 遍历方式，"dfs"（深度优先）或 "bfs"（广度优先）
    """
    ea = ctx.request_context.lifespan_context.ea
    raw = ea.traverse_note_tree(note_id, depth=depth, limit=limit, method=method)
    # trilium-py's traverse_note_tree returns list of dicts or list of tuples
    if raw and isinstance(raw[0], dict):
        return [
            NoteTreeItem(
                note_id=r.get("noteId", r.get("note_id", "")),
                title=r.get("title", ""),
                type=r.get("type", "text"),
                content=r.get("content", ""),
            )
            for r in raw
        ]
    return []


@mcp.tool(name="search_by_title")
def tool_search_by_title(
    title: str, ctx: Context[ServerSession, AppContext]
) -> list[NoteInfo]:
    """按标题精确搜索笔记。"""
    ea = ctx.request_context.lifespan_context.ea
    raw = ea.search_note(
        f"note.title %= '{title}'",
        fastSearch=False,
        orderBy=["title"],
    )
    return [_scrub_note(r) for r in raw.get("results", [])]


@mcp.tool(name="get_attachments")
def tool_get_attachments(
    note_id: str, ctx: Context[ServerSession, AppContext]
) -> list[dict]:
    """获取笔记的所有附件列表。

    Args:
        note_id: 笔记 ID
    """
    ea = ctx.request_context.lifespan_context.ea
    raw = ea.get_attachments(note_id)
    return [dict(r) for r in raw] if raw else []


@mcp.tool(name="save_revision")
def tool_save_revision(
    note_id: str, ctx: Context[ServerSession, AppContext]
) -> TodoResult:
    """手动保存笔记版本快照。

    Args:
        note_id: 笔记 ID
    """
    ea = ctx.request_context.lifespan_context.ea
    try:
        ea.save_revision(note_id)
        return TodoResult(ok=True, message=f"revision saved for {note_id}")
    except Exception as e:
        return TodoResult(ok=False, message=str(e))


@mcp.tool(name="get_backup")
def tool_get_backup(
    name: str, ctx: Context[ServerSession, AppContext]
) -> TodoResult:
    """创建数据库备份。

    Args:
        name: 备份名称
    """
    ea = ctx.request_context.lifespan_context.ea
    try:
        ea.backup(name)
        return TodoResult(ok=True, message=f"backup '{name}' created")
    except Exception as e:
        return TodoResult(ok=False, message=str(e))


# ── entrypoint ────────────────────────────────────────────────────────

def main():
    """Entrypoint.

    FastMCP is instantiated with host/port set to bind to 0.0.0.0:8000 inside
    containers so HTTP transports are reachable via Docker port mapping.
    """
    transport = os.environ.get("TRILIUM_MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.run(transport="sse")
    elif transport == "streamable-http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
