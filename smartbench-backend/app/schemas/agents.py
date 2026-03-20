"""Agent API schemas."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class AgentPromptRequest(BaseModel):
    workspace_id: uuid.UUID
    prompt: str = Field(min_length=1)
    session_id: uuid.UUID | None = None


class AgentToolAction(BaseModel):
    tool_name: str
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    status: str = "success"


class AgentPromptResponse(BaseModel):
    session_id: uuid.UUID
    response_text: str
    actions: list[AgentToolAction] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    references: list[dict[str, Any]] = Field(default_factory=list)
