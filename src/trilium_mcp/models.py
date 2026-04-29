"""Pydantic models for MCP structured output."""

from typing import Optional
from pydantic import BaseModel, Field


class AppInfo(BaseModel):
    """Trilium application metadata."""
    app_version: str = Field(description="Trilium server version")
    db_version: int = Field(description="Database version")
    sync_version: int = Field(description="Synchronization protocol version")
    build_date: str = Field(default="", description="Build date")
    build_revision: str = Field(default="", description="Build revision hash")
    utc_date_time: str = Field(default="", description="Current UTC time")


class NoteInfo(BaseModel):
    """Note metadata (without content)."""
    note_id: str = Field(description="Note ID")
    title: str = Field(default="", description="Note title")
    type: str = Field(default="text", description="Note type (text, code, image, etc.)")
    mime: str = Field(default="text/html", description="MIME type")
    is_protected: bool = Field(default=False, description="Whether note is password-protected")
    blob_id: Optional[str] = Field(default=None, description="Blob ID for non-text notes")
    parent_note_ids: list[str] = Field(default_factory=list, description="Parent note IDs")
    child_note_ids: list[str] = Field(default_factory=list, description="Child note IDs")


class SearchResult(BaseModel):
    """Search response wrapper."""
    results: list[NoteInfo] = Field(default_factory=list, description="Matched notes")


class BranchInfo(BaseModel):
    """Note clone/branch information."""
    branch_id: str = Field(description="Branch ID (parentNoteId_noteId)")
    note_id: str = Field(description="Note ID")
    parent_note_id: str = Field(description="Parent note ID")
    prefix: Optional[str] = Field(default=None, description="Branch prefix")
    note_position: int = Field(default=0, description="Position among siblings")
    is_expanded: bool = Field(default=False, description="Expanded state")
    utc_date_modified: str = Field(default="", description="Last modified time")


class AttributeInfo(BaseModel):
    """Note attribute (label or relation)."""
    attribute_id: str = Field(description="Attribute ID")
    note_id: str = Field(description="Owner note ID")
    type: str = Field(description="Attribute type: 'label' or 'relation'")
    name: str = Field(description="Attribute name")
    value: str = Field(default="", description="Attribute value")
    is_inheritable: bool = Field(default=False, description="Whether inherited by children")


class NoteContent(BaseModel):
    """Note content response."""
    note_id: str = Field(description="Note ID")
    content: str = Field(description="Note content (HTML string)")


class NoteTreeItem(BaseModel):
    """A single note discovered during tree traversal."""
    note_id: str = Field(description="Note ID")
    title: str = Field(default="", description="Note title")
    type: str = Field(default="text", description="Note type")
    content: str = Field(default="", description="Note content (HTML, may be truncated)")


class TodoResult(BaseModel):
    """Result of a TODO operation."""
    ok: bool = Field(description="Whether the operation succeeded")
    message: str = Field(default="", description="Status message")


class ExportInfo(BaseModel):
    """Export result metadata."""
    note_id: str = Field(description="Exported note ID")
    format: str = Field(description="Export format")
    success: bool = Field(default=True, description="Whether export succeeded")
    message: str = Field(default="", description="Status message")
