"""Immutable audit trail model."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import JSONType


class AuditEvent(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_workspace_id", "workspace_id"),
        Index("ix_audit_events_target", "target_type", "target_id"),
        Index("ix_audit_events_actor", "actor_user_id"),
    )

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id", ondelete="SET NULL"))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(String(128), nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONType)
    request_source: Mapped[str] = mapped_column(String(32), nullable=False, default="api")
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    reason: Mapped[str | None] = mapped_column(Text)
