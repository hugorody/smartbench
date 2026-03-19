"""File asset and association models."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import JSONType


class FileAsset(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "file_assets"
    __table_args__ = (Index("ix_file_assets_workspace_id", "workspace_id"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict | None] = mapped_column(JSONType)


class FileLink(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "file_links"
    __table_args__ = (
        Index("ix_file_links_workspace_id", "workspace_id"),
        UniqueConstraint(
            "workspace_id",
            "file_asset_id",
            "target_type",
            "target_id",
            name="uq_file_link_unique",
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    file_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("file_assets.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    relation: Mapped[str | None] = mapped_column(Text)
