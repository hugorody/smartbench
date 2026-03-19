"""Core API routes."""

from __future__ import annotations

from flask import jsonify

from app.blueprints.api import bp


@bp.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200


@bp.get("/meta")
def meta() -> object:
    return jsonify(
        {
            "name": "smartbench-backend",
            "agent_native": True,
            "warning": "Critical actions will require explicit confirmation in future versions.",
        }
    )
