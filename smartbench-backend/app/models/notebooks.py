"""Laboratory notebook models."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import JSONType


class NotebookTemplate(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "notebook_templates"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_notebook_template_workspace_name"),
        Index("ix_notebook_templates_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    sections = relationship(
        "NotebookTemplateSection", back_populates="template", cascade="all, delete-orphan"
    )


class NotebookTemplateSection(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "notebook_template_sections"
    __table_args__ = (
        UniqueConstraint("template_id", "name", name="uq_notebook_template_section_name"),
        Index("ix_notebook_template_sections_template_id", "template_id"),
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notebook_templates.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    section_schema: Mapped[dict] = mapped_column(JSONType, nullable=False)

    template = relationship("NotebookTemplate", back_populates="sections")


class NotebookEntry(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "notebook_entries"
    __table_args__ = (
        Index("ix_notebook_entries_workspace_id", "workspace_id"),
        UniqueConstraint("workspace_id", "entry_key", name="uq_notebook_entry_key"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("notebook_templates.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    entry_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")

    sections = relationship("NotebookEntrySection", back_populates="entry", cascade="all, delete-orphan")


class NotebookEntrySection(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "notebook_entry_sections"
    __table_args__ = (
        UniqueConstraint("entry_id", "name", name="uq_notebook_entry_section_name"),
        Index("ix_notebook_entry_sections_entry_id", "entry_id"),
    )

    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notebook_entries.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    content_markdown: Mapped[str | None] = mapped_column(Text)
    structured_data: Mapped[dict | None] = mapped_column(JSONType)

    entry = relationship("NotebookEntry", back_populates="sections")


class NotebookLink(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "notebook_links"
    __table_args__ = (
        Index("ix_notebook_links_workspace_id", "workspace_id"),
        UniqueConstraint(
            "workspace_id",
            "notebook_entry_id",
            "target_type",
            "target_id",
            name="uq_notebook_link_unique",
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    notebook_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notebook_entries.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
