from flask import Blueprint

bp = Blueprint("results", __name__, url_prefix="/api/results")

from app.blueprints.results import routes  # noqa: E402,F401
