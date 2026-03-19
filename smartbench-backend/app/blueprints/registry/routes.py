"""Entity type and entity API routes."""

from __future__ import annotations

import uuid

from flask import jsonify, request
from pydantic import ValidationError as PydanticValidationError

from app.blueprints.registry import bp
from app.extensions import db
from app.schemas.registry import EntityCreate, EntityTypeCreate, EntityTypeVersionCreate, EntityUpdate
from app.services.exceptions import NotFoundError, ServiceError, ValidationError
from app.services.registry_service import RegistryService
from app.utils.request_context import get_identity


@bp.get("/entity-types")
def list_entity_types() -> object:
    workspace_id = request.args.get("workspace_id")
    if not workspace_id:
        return jsonify({"error": "workspace_id_required"}), 400
    entity_types = RegistryService.list_entity_types(db.session, uuid.UUID(workspace_id))
    return jsonify(
        [
            {
                "id": str(entity_type.id),
                "name": entity_type.name,
                "slug": entity_type.slug,
                "active_version_id": str(entity_type.active_version_id)
                if entity_type.active_version_id
                else None,
            }
            for entity_type in entity_types
        ]
    )


@bp.post("/entity-types")
def create_entity_type() -> object:
    try:
        payload = EntityTypeCreate.model_validate(request.get_json(force=True))
        entity_type = RegistryService.create_entity_type(db.session, payload, get_identity())
        return jsonify({"id": str(entity_type.id), "name": entity_type.name}), 201
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except ServiceError as exc:
        return jsonify({"error": "service_error", "message": str(exc)}), 400


@bp.post("/entity-types/<entity_type_id>/versions")
def create_entity_type_version(entity_type_id: str) -> object:
    try:
        payload_data = request.get_json(force=True)
        payload_data["entity_type_id"] = entity_type_id
        payload = EntityTypeVersionCreate.model_validate(payload_data)
        version = RegistryService.create_entity_type_version(db.session, payload, get_identity())
        return jsonify({"id": str(version.id), "version": version.version, "status": version.status}), 201
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except ServiceError as exc:
        return jsonify({"error": "service_error", "message": str(exc)}), 400


@bp.get("/entities")
def list_entities() -> object:
    workspace_id = request.args.get("workspace_id")
    query = request.args.get("q")
    if not workspace_id:
        return jsonify({"error": "workspace_id_required"}), 400

    workspace_uuid = uuid.UUID(workspace_id)
    entities = (
        RegistryService.search_entities(db.session, workspace_uuid, query)
        if query
        else RegistryService.list_entities(db.session, workspace_uuid)
    )

    return jsonify(
        [
            {
                "id": str(entity.id),
                "external_id": entity.external_id,
                "name": entity.name,
                "status": entity.status,
                "entity_type_id": str(entity.entity_type_id),
                "data": entity.data,
            }
            for entity in entities
        ]
    )


@bp.post("/entities")
def create_entity() -> object:
    try:
        payload = EntityCreate.model_validate(request.get_json(force=True))
        entity = RegistryService.create_entity(db.session, payload, get_identity())
        return jsonify({"id": str(entity.id), "external_id": entity.external_id}), 201
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except (ValidationError, NotFoundError) as exc:
        return jsonify({"error": "validation_error", "message": str(exc)}), 400


@bp.patch("/entities/<entity_id>")
def update_entity(entity_id: str) -> object:
    try:
        payload = EntityUpdate.model_validate(request.get_json(force=True))
        entity = RegistryService.update_entity(db.session, uuid.UUID(entity_id), payload, get_identity())
        return jsonify({"id": str(entity.id), "name": entity.name, "status": entity.status})
    except ValueError:
        return jsonify({"error": "invalid_entity_id"}), 400
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400
    except ServiceError as exc:
        return jsonify({"error": "service_error", "message": str(exc)}), 400
