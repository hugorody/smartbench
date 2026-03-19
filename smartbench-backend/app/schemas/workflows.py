"""Workflow payload schemas."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class WorkflowStateInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=255)
    order_index: int = 0
    is_initial: bool = False
    is_terminal: bool = False


class WorkflowTransitionInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    from_state: str = Field(min_length=1, max_length=100)
    to_state: str = Field(min_length=1, max_length=100)
    required_fields: list[str] | None = None
    approval_required: bool = False


class WorkflowDefinitionCreate(BaseModel):
    workspace_id: uuid.UUID
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    states: list[WorkflowStateInput] = Field(min_length=1)
    transitions: list[WorkflowTransitionInput] = Field(min_length=1)


class WorkflowRunStart(BaseModel):
    workspace_id: uuid.UUID
    workflow_definition_id: uuid.UUID
    run_key: str = Field(min_length=2, max_length=64)
    context_data: dict[str, Any] | None = None


class WorkflowTransitionApply(BaseModel):
    transition_name: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] | None = None
