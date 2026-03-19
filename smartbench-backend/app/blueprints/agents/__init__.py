from flask import Blueprint

bp = Blueprint("agents", __name__, url_prefix="/api/agents")

from app.blueprints.agents import routes  # noqa: E402,F401
