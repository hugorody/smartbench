"""Workspace API routes."""

from __future__ import annotations

import uuid

from flask import jsonify, request
from pydantic import ValidationError as PydanticValidationError

from app.blueprints.workspaces import bp
from app.extensions import db
from app.models import Workspace
from app.schemas.identity import WorkspaceCreate
from app.services.exceptions import ServiceError
from app.services.workspace_service import WorkspaceService
from app.utils.request_context import get_identity


@bp.get("")
def list_workspaces() -> object:
    workspaces = db.session.query(Workspace).order_by(Workspace.name).all()
    return jsonify(
        [
            {
                "id": str(workspace.id),
                "name": workspace.name,
                "slug": workspace.slug,
                "description": workspace.description,
            }
            for workspace in workspaces
        ]
    )


@bp.post("")
def create_workspace() -> object:
    try:
        payload = WorkspaceCreate.model_validate(request.get_json(force=True))
        workspace = WorkspaceService.create_workspace(db.session, payload, get_identity())
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except ServiceError as exc:
        return jsonify({"error": "service_error", "message": str(exc)}), 400

    return (
        jsonify(
            {
                "id": str(workspace.id),
                "name": workspace.name,
                "slug": workspace.slug,
                "description": workspace.description,
            }
        ),
        201,
    )


@bp.post("/switch/<workspace_id>")
def switch_workspace(workspace_id: str) -> object:
    from flask import session

    try:
        workspace_uuid = uuid.UUID(workspace_id)
    except ValueError:
        return jsonify({"error": "invalid_workspace_id"}), 400

    workspace = db.session.get(Workspace, workspace_uuid)
    if workspace is None:
        return jsonify({"error": "not_found"}), 404

    session["active_workspace_id"] = str(workspace.id)
    return jsonify({"message": "ok", "workspace_id": str(workspace.id)})
