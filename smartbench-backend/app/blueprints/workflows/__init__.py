from flask import Blueprint

bp = Blueprint("workflows", __name__, url_prefix="/api/workflows")

from app.blueprints.workflows import routes  # noqa: E402,F401
