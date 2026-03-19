from flask import Blueprint

bp = Blueprint("notebooks", __name__, url_prefix="/api/notebooks")

from app.blueprints.notebooks import routes  # noqa: E402,F401
