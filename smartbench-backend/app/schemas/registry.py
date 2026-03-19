"""Registry payload schemas."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

FieldType = Literal["string", "number", "boolean", "date", "enum", "json", "entity_ref"]


class EntityTypeFieldInput(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=255)
    field_type: FieldType
    is_required: bool = False
    is_array: bool = False
    enum_values: list[str] | None = None
    relationship_target: str | None = None
    validations: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_enum_requirements(self) -> EntityTypeFieldInput:
        if self.field_type == "enum" and not self.enum_values:
            raise ValueError("enum_values is required for enum field_type")
        return self


class EntityTypeCreate(BaseModel):
    workspace_id: uuid.UUID
    name: str = Field(min_length=2, max_length=128)
    slug: str = Field(min_length=2, max_length=128)
    description: str | None = None
    fields: list[EntityTypeFieldInput] = Field(default_factory=list)


class EntityTypeVersionCreate(BaseModel):
    entity_type_id: uuid.UUID
    status: Literal["draft", "active", "deprecated"] = "draft"
    fields: list[EntityTypeFieldInput] = Field(default_factory=list)


class EntityCreate(BaseModel):
    workspace_id: uuid.UUID
    entity_type_id: uuid.UUID
    external_id: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    status: str = Field(default="active", max_length=32)
    data: dict[str, Any]


class EntityUpdate(BaseModel):
    name: str | None = None
    status: str | None = Field(default=None, max_length=32)
    data: dict[str, Any] | None = None
