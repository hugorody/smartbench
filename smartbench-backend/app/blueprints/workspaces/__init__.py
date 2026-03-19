from flask import Blueprint

bp = Blueprint("workspaces", __name__, url_prefix="/api/workspaces")

from app.blueprints.workspaces import routes  # noqa: E402,F401
