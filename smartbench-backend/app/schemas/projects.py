"""Project payload schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    workspace_id: uuid.UUID
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None


class ProjectResourceLinkCreate(BaseModel):
    workspace_id: uuid.UUID
    project_id: uuid.UUID
    resource_type: str = Field(min_length=2, max_length=64)
    resource_id: str = Field(min_length=2, max_length=64)
