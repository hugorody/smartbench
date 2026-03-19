"""Pytest fixtures for SmartBench backend."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.pool import StaticPool

from app import create_app
from app.extensions import db
from app.models import Permission, Role, RolePermission, User, Workspace
from app.security.rbac import PermissionCodes
from app.utils.request_context import IdentityContext


@pytest.fixture()
def app():
    app = create_app("testing")
    app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite+pysqlite://",
        SQLALCHEMY_ENGINE_OPTIONS={
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        },
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def session(app):
    with app.app_context():
        yield db.session


@pytest.fixture()
def identity(session) -> IdentityContext:
    workspace = Workspace(name="Test Workspace", slug=f"test-{uuid.uuid4().hex[:8]}")
    user = User(email=f"user-{uuid.uuid4().hex[:6]}@test.local", full_name="Test User")
    role = Role(workspace_id=None, name=f"test-role-{uuid.uuid4().hex[:6]}")
    session.add_all([workspace, user, role])
    session.flush()

    for code in [
        PermissionCodes.ENTITY_TYPE_WRITE,
        PermissionCodes.ENTITY_WRITE,
        PermissionCodes.RESULT_WRITE,
        PermissionCodes.WORKFLOW_WRITE,
    ]:
        permission = Permission(code=f"{code}-{uuid.uuid4().hex[:4]}", description=code)
        session.add(permission)
        session.flush()
        session.add(RolePermission(role_id=role.id, permission_id=permission.id))

    session.commit()
    return IdentityContext(user_id=user.id, workspace_id=workspace.id, source="test")
