"""RBAC checks for workspace-scoped permissions."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Membership, Permission, RolePermission


class PermissionCodes:
    ENTITY_TYPE_WRITE = "entity_type:write"
    ENTITY_WRITE = "entity:write"
    NOTEBOOK_WRITE = "notebook:write"
    RESULT_WRITE = "result:write"
    WORKFLOW_WRITE = "workflow:write"
    AUDIT_READ = "audit:read"
    AGENT_USE = "agent:use"


class RBACService:
    """Role-based permission service."""

    @staticmethod
    def has_permission(
        session: Session,
        *,
        user_id: uuid.UUID | None,
        workspace_id: uuid.UUID | None,
        permission_code: str,
    ) -> bool:
        if user_id is None or workspace_id is None:
            return False

        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Membership, Membership.role_id == RolePermission.role_id)
            .where(Membership.user_id == user_id)
            .where(Membership.workspace_id == workspace_id)
            .where(Permission.code == permission_code)
            .limit(1)
        )
        return session.execute(stmt).scalar_one_or_none() is not None
