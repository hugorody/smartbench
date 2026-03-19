"""Notebook API routes."""

from __future__ import annotations

import uuid

from flask import jsonify, request
from pydantic import ValidationError as PydanticValidationError

from app.blueprints.notebooks import bp
from app.extensions import db
from app.schemas.notebooks import NotebookEntryCreate, NotebookSectionAppend, NotebookTemplateCreate
from app.services.exceptions import ServiceError
from app.services.notebook_service import NotebookService
from app.utils.request_context import get_identity


@bp.get("/templates")
def list_templates() -> object:
    workspace_id = request.args.get("workspace_id")
    if not workspace_id:
        return jsonify({"error": "workspace_id_required"}), 400

    templates = NotebookService.list_templates(db.session, uuid.UUID(workspace_id))
    return jsonify(
        [{"id": str(template.id), "name": template.name, "description": template.description} for template in templates]
    )


@bp.post("/templates")
def create_template() -> object:
    try:
        payload = NotebookTemplateCreate.model_validate(request.get_json(force=True))
        template = NotebookService.create_template(db.session, payload, get_identity())
        return jsonify({"id": str(template.id), "name": template.name}), 201
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except ServiceError as exc:
        return jsonify({"error": "service_error", "message": str(exc)}), 400


@bp.get("/entries")
def list_entries() -> object:
    workspace_id = request.args.get("workspace_id")
    if not workspace_id:
        return jsonify({"error": "workspace_id_required"}), 400

    entries = NotebookService.list_entries(db.session, uuid.UUID(workspace_id))
    return jsonify(
        [
            {
                "id": str(entry.id),
                "entry_key": entry.entry_key,
                "title": entry.title,
                "status": entry.status,
            }
            for entry in entries
        ]
    )


@bp.post("/entries")
def create_entry() -> object:
    try:
        payload = NotebookEntryCreate.model_validate(request.get_json(force=True))
        entry = NotebookService.create_entry(db.session, payload, get_identity())
        return jsonify({"id": str(entry.id), "entry_key": entry.entry_key}), 201
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except ServiceError as exc:
        return jsonify({"error": "service_error", "message": str(exc)}), 400


@bp.post("/entries/<entry_id>/sections")
def append_entry_section(entry_id: str) -> object:
    try:
        payload = NotebookSectionAppend.model_validate(request.get_json(force=True))
        section = NotebookService.append_section(db.session, uuid.UUID(entry_id), payload, get_identity())
        return jsonify({"id": str(section.id), "name": section.name}), 201
    except ValueError:
        return jsonify({"error": "invalid_entry_id"}), 400
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except ServiceError as exc:
        return jsonify({"error": "service_error", "message": str(exc)}), 400
