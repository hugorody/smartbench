"""Projects API routes."""

from __future__ import annotations

import uuid

from flask import jsonify, request
from pydantic import ValidationError as PydanticValidationError

from app.blueprints.projects import bp
from app.extensions import db
from app.schemas.projects import ProjectCreate, ProjectResourceLinkCreate
from app.services.exceptions import ServiceError
from app.services.project_service import ProjectService
from app.utils.request_context import get_identity


@bp.get("")
def list_projects() -> object:
    workspace_id = request.args.get("workspace_id")
    if not workspace_id:
        return jsonify({"error": "workspace_id_required"}), 400

    try:
        workspace_uuid = uuid.UUID(workspace_id)
    except ValueError:
        return jsonify({"error": "invalid_workspace_id"}), 400

    query = request.args.get("q", "").strip() or None
    projects = ProjectService.list_projects(db.session, workspace_uuid, search=query)
    link_counts = ProjectService.project_link_counts(db.session, workspace_uuid)

    return jsonify(
        [
            {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "resource_count": link_counts.get(project.id, 0),
            }
            for project in projects
        ]
    )


@bp.post("")
def create_project() -> object:
    try:
        payload = ProjectCreate.model_validate(request.get_json(force=True))
        project = ProjectService.create_project(db.session, payload, get_identity())
        return jsonify({"id": str(project.id), "name": project.name}), 201
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except ServiceError as exc:
        return jsonify({"error": "service_error", "message": str(exc)}), 400


@bp.post("/<project_id>/links")
def link_project_resource(project_id: str) -> object:
    try:
        payload_data = request.get_json(force=True)
        payload_data["project_id"] = project_id
        payload = ProjectResourceLinkCreate.model_validate(payload_data)
        link = ProjectService.link_resource(
            db.session,
            workspace_id=payload.workspace_id,
            project_id=payload.project_id,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            identity=get_identity(),
        )
        return (
            jsonify(
                {
                    "id": str(link.id),
                    "project_id": str(link.project_id),
                    "resource_type": link.resource_type,
                    "resource_id": link.resource_id,
                }
            ),
            201,
        )
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except ServiceError as exc:
        return jsonify({"error": "service_error", "message": str(exc)}), 400
