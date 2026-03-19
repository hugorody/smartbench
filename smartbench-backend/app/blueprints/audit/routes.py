"""Audit and introspection API routes."""

from __future__ import annotations

import uuid

from flask import jsonify, request

from app.blueprints.audit import bp
from app.extensions import db
from app.models import AuditEvent
from app.services.introspection_service import IntrospectionService


@bp.get("/events")
def list_audit_events() -> object:
    workspace_id = request.args.get("workspace_id")
    if not workspace_id:
        return jsonify({"error": "workspace_id_required"}), 400

    events = (
        db.session.query(AuditEvent)
        .filter(AuditEvent.workspace_id == uuid.UUID(workspace_id))
        .order_by(AuditEvent.created_at.desc())
        .limit(200)
        .all()
    )
    return jsonify(
        [
            {
                "id": str(event.id),
                "action": event.action,
                "target_type": event.target_type,
                "target_id": event.target_id,
                "payload": event.payload,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]
    )


@bp.get("/schema-introspection")
def schema_introspection() -> object:
    workspace_id = request.args.get("workspace_id")
    if not workspace_id:
        return jsonify({"error": "workspace_id_required"}), 400
    workspace_uuid = uuid.UUID(workspace_id)

    return jsonify(
        {
            "entity_types": IntrospectionService.entity_types(db.session, workspace_uuid),
            "notebook_templates": IntrospectionService.notebook_templates(db.session, workspace_uuid),
            "result_schemas": IntrospectionService.result_schemas(db.session, workspace_uuid),
            "workflows": IntrospectionService.workflows(db.session, workspace_uuid),
        }
    )
