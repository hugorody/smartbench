"""Workflow API routes."""

from __future__ import annotations

import uuid

from flask import jsonify, request
from pydantic import ValidationError as PydanticValidationError

from app.blueprints.workflows import bp
from app.extensions import db
from app.schemas.workflows import WorkflowDefinitionCreate, WorkflowRunStart, WorkflowTransitionApply
from app.services.exceptions import ServiceError
from app.services.workflow_service import WorkflowService
from app.utils.request_context import get_identity


@bp.get("/definitions")
def list_definitions() -> object:
    workspace_id = request.args.get("workspace_id")
    if not workspace_id:
        return jsonify({"error": "workspace_id_required"}), 400

    definitions = WorkflowService.list_definitions(db.session, uuid.UUID(workspace_id))
    return jsonify([{"id": str(defn.id), "name": defn.name} for defn in definitions])


@bp.post("/definitions")
def create_definition() -> object:
    try:
        payload = WorkflowDefinitionCreate.model_validate(request.get_json(force=True))
        definition = WorkflowService.create_definition(db.session, payload, get_identity())
        return jsonify({"id": str(definition.id), "name": definition.name}), 201
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except ServiceError as exc:
        return jsonify({"error": "service_error", "message": str(exc)}), 400


@bp.get("/runs")
def list_runs() -> object:
    workspace_id = request.args.get("workspace_id")
    if not workspace_id:
        return jsonify({"error": "workspace_id_required"}), 400

    runs = WorkflowService.list_runs(db.session, uuid.UUID(workspace_id))
    return jsonify(
        [{"id": str(run.id), "run_key": run.run_key, "current_state": run.current_state} for run in runs]
    )


@bp.post("/runs")
def start_run() -> object:
    try:
        payload = WorkflowRunStart.model_validate(request.get_json(force=True))
        run = WorkflowService.start_run(db.session, payload, get_identity())
        return jsonify({"id": str(run.id), "run_key": run.run_key, "current_state": run.current_state}), 201
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except ServiceError as exc:
        return jsonify({"error": "service_error", "message": str(exc)}), 400


@bp.post("/runs/<run_id>/transition")
def transition_run(run_id: str) -> object:
    try:
        payload = WorkflowTransitionApply.model_validate(request.get_json(force=True))
        run = WorkflowService.transition_run(db.session, uuid.UUID(run_id), payload, get_identity())
        return jsonify({"id": str(run.id), "current_state": run.current_state})
    except ValueError:
        return jsonify({"error": "invalid_run_id"}), 400
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except ServiceError as exc:
        return jsonify({"error": "service_error", "message": str(exc)}), 400
