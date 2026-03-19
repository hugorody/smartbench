"""Result schema and record models."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import JSONType


class ResultSchema(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "result_schemas"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_result_schema_workspace_name"),
        Index("ix_result_schemas_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    fields = relationship("ResultSchemaField", back_populates="schema", cascade="all, delete-orphan")


class ResultSchemaField(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "result_schema_fields"
    __table_args__ = (
        UniqueConstraint("result_schema_id", "name", name="uq_result_schema_field_name"),
        Index("ix_result_schema_fields_result_schema_id", "result_schema_id"),
    )

    result_schema_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("result_schemas.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    field_type: Mapped[str] = mapped_column(String(64), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enum_values: Mapped[list[str] | None] = mapped_column(JSONType)
    validations: Mapped[dict | None] = mapped_column(JSONType)

    schema = relationship("ResultSchema", back_populates="fields")


class ResultRecord(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "result_records"
    __table_args__ = (Index("ix_result_records_workspace_id", "workspace_id"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    result_schema_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("result_schemas.id", ondelete="RESTRICT"), nullable=False
    )
    record_key: Mapped[str] = mapped_column(String(64), nullable=False)
    data: Mapped[dict] = mapped_column(JSONType, nullable=False)

    schema = relationship("ResultSchema")
