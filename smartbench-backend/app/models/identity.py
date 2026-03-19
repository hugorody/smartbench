"""Identity and access control models."""

from __future__ import annotations

import uuid

from flask_login import UserMixin
from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Workspace(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    memberships = relationship("Membership", back_populates="workspace", cascade="all, delete-orphan")


class User(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, UserMixin, db.Model):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")

    def get_id(self) -> str:
        return str(self.id)


class Role(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_role_workspace_name"),)

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    memberships = relationship("Membership", back_populates="role")


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class RolePermission(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
        Index("ix_role_permissions_role_id", "role_id"),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission")


class Membership(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_membership_workspace_user"),
        Index("ix_memberships_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)

    workspace = relationship("Workspace", back_populates="memberships")
    user = relationship("User", back_populates="memberships")
    role = relationship("Role", back_populates="memberships")
