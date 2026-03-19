from flask import Blueprint

bp = Blueprint("registry", __name__, url_prefix="/api/registry")

from app.blueprints.registry import routes  # noqa: E402,F401
