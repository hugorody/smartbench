"""Project organization models."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Project(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    """Workspace-scoped project container for scientific resources."""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_project_workspace_name"),
        Index("ix_projects_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    resource_links = relationship(
        "ProjectResourceLink",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectResourceLink(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    """Generic link between a project and any workspace resource."""

    __tablename__ = "project_resource_links"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "resource_type",
            "resource_id",
            name="uq_project_resource_link",
        ),
        Index("ix_project_resource_links_workspace_id", "workspace_id"),
        Index("ix_project_resource_links_project_id", "project_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False)

    project = relationship("Project", back_populates="resource_links")
