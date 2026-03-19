"""Dynamic scientific registry models."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import JSONType


class EntityType(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "entity_types"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_entity_type_workspace_name"),
        Index("ix_entity_types_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    active_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "entity_type_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_entity_types_active_version_id",
        )
    )

    versions = relationship(
        "EntityTypeVersion",
        back_populates="entity_type",
        cascade="all, delete-orphan",
        foreign_keys="EntityTypeVersion.entity_type_id",
    )
    active_version = relationship("EntityTypeVersion", foreign_keys=[active_version_id], post_update=True)
    entities = relationship("Entity", back_populates="entity_type")


class EntityTypeVersion(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "entity_type_versions"
    __table_args__ = (
        UniqueConstraint("entity_type_id", "version", name="uq_entity_type_version"),
        Index("ix_entity_type_versions_entity_type_id", "entity_type_id"),
    )

    entity_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entity_types.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    schema_snapshot: Mapped[dict] = mapped_column(JSONType, nullable=False)

    entity_type = relationship("EntityType", back_populates="versions", foreign_keys=[entity_type_id])
    fields = relationship("EntityTypeField", back_populates="entity_type_version", cascade="all, delete-orphan")


class EntityTypeField(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "entity_type_fields"
    __table_args__ = (
        UniqueConstraint("entity_type_version_id", "name", name="uq_entity_type_field_name"),
        Index("ix_entity_type_fields_entity_type_version_id", "entity_type_version_id"),
    )

    entity_type_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entity_type_versions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    field_type: Mapped[str] = mapped_column(String(64), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_array: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enum_values: Mapped[list[str] | None] = mapped_column(JSONType)
    relationship_target: Mapped[str | None] = mapped_column(String(128))
    validations: Mapped[dict | None] = mapped_column(JSONType)

    entity_type_version = relationship("EntityTypeVersion", back_populates="fields")


class Entity(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("workspace_id", "entity_type_id", "external_id", name="uq_entity_external_id"),
        Index("ix_entities_workspace_id", "workspace_id"),
        Index("ix_entities_entity_type_id", "entity_type_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    entity_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entity_types.id", ondelete="RESTRICT"), nullable=False
    )
    entity_type_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entity_type_versions.id", ondelete="RESTRICT"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    data: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)

    entity_type = relationship("EntityType", back_populates="entities")


class EntityRelationship(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "entity_relationships"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            name="uq_entity_relationship",
        ),
        Index("ix_entity_relationships_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONType)
