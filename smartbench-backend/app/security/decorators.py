"""Permission decorators for API routes."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import jsonify

from app.extensions import db
from app.security.rbac import RBACService
from app.utils.request_context import get_identity

RouteFn = Callable[..., Any]


def require_permission(permission_code: str) -> Callable[[RouteFn], RouteFn]:
    """Require workspace-scoped permission for route access."""

    def decorator(fn: RouteFn) -> RouteFn:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            identity = get_identity()
            if not RBACService.has_permission(
                db.session,
                user_id=identity.user_id,
                workspace_id=identity.workspace_id,
                permission_code=permission_code,
            ):
                return jsonify({"error": "forbidden", "permission": permission_code}), 403
            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
