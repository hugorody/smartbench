"""Results payload schemas."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

FieldType = Literal["string", "number", "boolean", "date", "enum", "json"]


class ResultSchemaFieldInput(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=255)
    field_type: FieldType
    is_required: bool = False
    enum_values: list[str] | None = None
    validations: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_enum(self) -> ResultSchemaFieldInput:
        if self.field_type == "enum" and not self.enum_values:
            raise ValueError("enum_values required for enum field")
        return self


class ResultSchemaCreate(BaseModel):
    workspace_id: uuid.UUID
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    fields: list[ResultSchemaFieldInput] = Field(default_factory=list)


class ResultRecordCreate(BaseModel):
    workspace_id: uuid.UUID
    result_schema_id: uuid.UUID
    record_key: str = Field(min_length=2, max_length=64)
    data: dict[str, Any]
