"""Notebook payload schemas."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class NotebookTemplateSectionInput(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=255)
    order_index: int = 0
    section_schema: dict[str, Any] = Field(default_factory=dict)


class NotebookTemplateCreate(BaseModel):
    workspace_id: uuid.UUID
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    sections: list[NotebookTemplateSectionInput] = Field(default_factory=list)


class NotebookEntryCreate(BaseModel):
    workspace_id: uuid.UUID
    template_id: uuid.UUID | None = None
    title: str = Field(min_length=2, max_length=255)
    entry_key: str = Field(min_length=2, max_length=64)
    status: str = Field(default="draft", max_length=32)


class NotebookSectionAppend(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    content_markdown: str | None = None
    structured_data: dict[str, Any] | None = None
