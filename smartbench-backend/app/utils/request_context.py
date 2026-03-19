"""Request identity extraction for auditable service operations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from flask import g, request, session
from flask_login import current_user


@dataclass(slots=True)
class IdentityContext:
    user_id: uuid.UUID | None
    workspace_id: uuid.UUID | None
    source: str = "api"



def _to_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None



def resolve_identity() -> IdentityContext:
    """Resolve identity from user session and request headers."""
    user_id: uuid.UUID | None = None
    if getattr(current_user, "is_authenticated", False):
        user_id = current_user.id

    header_user_id = _to_uuid(request.headers.get("X-User-Id"))
    header_workspace_id = _to_uuid(request.headers.get("X-Workspace-Id"))
    session_workspace_id = _to_uuid(session.get("active_workspace_id"))

    if header_user_id is not None:
        user_id = header_user_id

    return IdentityContext(
        user_id=user_id,
        workspace_id=header_workspace_id or session_workspace_id,
        source="web" if request.blueprint == "dashboard" else "api",
    )



def get_identity() -> IdentityContext:
    identity = getattr(g, "identity", None)
    if identity is None:
        identity = resolve_identity()
        g.identity = identity
    return identity
