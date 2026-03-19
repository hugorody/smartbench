"""Identity schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    slug: str = Field(min_length=2, max_length=100)
    description: str | None = None


class UserCreate(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    full_name: str = Field(min_length=2, max_length=255)


class MembershipAssign(BaseModel):
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    role_id: uuid.UUID
