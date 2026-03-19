"""SmartBench application factory."""

from __future__ import annotations

import uuid

from flask import Flask, jsonify

from app.blueprints.agents import bp as agents_bp
from app.blueprints.api import bp as api_bp
from app.blueprints.audit import bp as audit_bp
from app.blueprints.auth import bp as auth_bp
from app.blueprints.dashboard import bp as dashboard_bp
from app.blueprints.notebooks import bp as notebooks_bp
from app.blueprints.projects import bp as projects_bp
from app.blueprints.registry import bp as registry_bp
from app.blueprints.results import bp as results_bp
from app.blueprints.workflows import bp as workflows_bp
from app.blueprints.workspaces import bp as workspaces_bp
from app.config import config_by_name
from app.extensions import db, login_manager, migrate
from app.models import User
from app.utils.logging import configure_logging
from app.utils.request_context import resolve_identity


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    cfg_name = config_name or "development"
    app.config.from_object(config_by_name[cfg_name])

    configure_logging(app.config["LOG_LEVEL"])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        try:
            return db.session.get(User, uuid.UUID(user_id))
        except ValueError:
            return None

    @app.before_request
    def inject_identity() -> None:
        from flask import g

        g.identity = resolve_identity()

    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return {"status": "ok"}, 200

    @app.errorhandler(404)
    def not_found(_: Exception) -> tuple[dict[str, str], int]:
        return {"error": "not_found"}, 404

    @app.errorhandler(500)
    def server_error(_: Exception) -> tuple[dict[str, str], int]:
        return {"error": "internal_server_error"}, 500

    @app.get("/api")
    def api_root() -> object:
        return jsonify({"name": "smartbench-backend", "version": "0.1.0"})

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(workspaces_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(registry_bp)
    app.register_blueprint(notebooks_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(workflows_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(agents_bp)

    return app
