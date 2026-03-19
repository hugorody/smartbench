"""Agent console API routes."""

from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError as PydanticValidationError

from app.blueprints.agents import bp
from app.extensions import db
from app.schemas.agents import AgentPromptRequest
from app.services.agent_service import AgentService
from app.utils.request_context import get_identity


@bp.post("/prompt")
def prompt_agent() -> object:
    try:
        payload = AgentPromptRequest.model_validate(request.get_json(force=True))
    except PydanticValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400

    service = AgentService()
    result = service.run_prompt(
        db.session,
        workspace_id=payload.workspace_id,
        prompt=payload.prompt,
        session_id=payload.session_id,
        identity=get_identity(),
    )
    return jsonify(result.response.model_dump())
