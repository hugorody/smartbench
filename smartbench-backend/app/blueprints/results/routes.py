"""Results API routes."""

from __future__ import annotations

import uuid

from flask import jsonify, request
from pydantic import ValidationError as PydanticValidationError

from app.blueprints.results import bp
from app.extensions import db
from app.schemas.results import ResultRecordCreate, ResultSchemaCreate
from app.services.exceptions import ServiceError
from app.services.result_service import ResultService
from app.utils.request_context import get_identity


@bp.get("/schemas")
def list_schemas() -> object:
    workspace_id = request.args.get("workspace_id")
    if not workspace_id:
        return jsonify({"error": "workspace_id_required"}), 400

    schemas = ResultService.list_schemas(db.session, uuid.UUID(workspace_id))
    return jsonify([{"id": str(schema.id), "name": schema.name} for schema in schemas])


@bp.post("/schemas")
def create_schema() -> object:
    try:
        payload = ResultSchemaCreate.model_validate(request.get_json(force=True))
        schema = ResultService.create_schema(db.session, payload, get_identity())
        return jsonify({"id": str(schema.id), "name": schema.name}), 201
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except ServiceError as exc:
        return jsonify({"error": "service_error", "message": str(exc)}), 400


@bp.get("/records")
def list_records() -> object:
    workspace_id = request.args.get("workspace_id")
    if not workspace_id:
        return jsonify({"error": "workspace_id_required"}), 400

    records = ResultService.list_records(db.session, uuid.UUID(workspace_id))
    return jsonify([{"id": str(record.id), "record_key": record.record_key, "data": record.data} for record in records])


@bp.post("/records")
def create_record() -> object:
    try:
        payload = ResultRecordCreate.model_validate(request.get_json(force=True))
        record = ResultService.create_record(db.session, payload, get_identity())
        return jsonify({"id": str(record.id), "record_key": record.record_key}), 201
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except ServiceError as exc:
        return jsonify({"error": "service_error", "message": str(exc)}), 400
