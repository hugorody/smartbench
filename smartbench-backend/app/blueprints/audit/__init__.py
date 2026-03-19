from flask import Blueprint

bp = Blueprint("audit", __name__, url_prefix="/api/audit")

from app.blueprints.audit import routes  # noqa: E402,F401
