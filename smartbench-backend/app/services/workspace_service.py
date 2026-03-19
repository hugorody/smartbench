"""Workspace and identity services."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Membership, Role, User, Workspace
from app.schemas.identity import WorkspaceCreate
from app.services.audit_service import AuditService
from app.services.exceptions import NotFoundError
from app.utils.request_context import IdentityContext


class WorkspaceService:
    """Workspace CRUD operations."""

    @staticmethod
    def create_workspace(
        session: Session,
        payload: WorkspaceCreate,
        identity: IdentityContext,
    ) -> Workspace:
        workspace = Workspace(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(workspace)
        session.flush()
        AuditService.record(
            session,
            identity,
            action="workspace.create",
            target_type="workspace",
            target_id=workspace.id,
            payload={"name": workspace.name, "slug": workspace.slug},
        )
        session.commit()
        return workspace

    @staticmethod
    def list_workspaces_for_user(session: Session, user_id: uuid.UUID) -> list[Workspace]:
        stmt = (
            select(Workspace)
            .join(Membership, Membership.workspace_id == Workspace.id)
            .where(Membership.user_id == user_id)
            .order_by(Workspace.name)
        )
        return list(session.scalars(stmt).all())


class AuthService:
    """Auth helpers for scaffold login flow."""

    @staticmethod
    def get_or_create_user(session: Session, email: str, full_name: str) -> User:
        stmt = select(User).where(User.email == email)
        user = session.scalar(stmt)
        if user is not None:
            return user

        user = User(email=email, full_name=full_name)
        session.add(user)
        session.commit()
        return user

    @staticmethod
    def set_workspace_membership(
        session: Session,
        *,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        role_name: str,
        actor_id: uuid.UUID | None,
    ) -> Membership:
        role = session.scalar(
            select(Role)
            .where(Role.workspace_id == workspace_id)
            .where(Role.name == role_name)
            .limit(1)
        )
        if role is None:
            raise NotFoundError(f"Role {role_name} not found in workspace")

        existing = session.scalar(
            select(Membership)
            .where(Membership.user_id == user_id)
            .where(Membership.workspace_id == workspace_id)
            .limit(1)
        )
        if existing:
            return existing

        membership = Membership(
            user_id=user_id,
            workspace_id=workspace_id,
            role_id=role.id,
            created_by=actor_id,
            updated_by=actor_id,
        )
        session.add(membership)
        session.commit()
        return membership
