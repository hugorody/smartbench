"""Session-based auth scaffold routes."""

from __future__ import annotations

from flask import flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user

from app.blueprints.auth import bp
from app.extensions import db
from app.models import Workspace
from app.services.workspace_service import AuthService


@bp.route("/login", methods=["GET", "POST"])
def login() -> object:
    if request.method == "GET":
        return render_template("auth/login.html")

    email = request.form.get("email", "").strip().lower()
    full_name = request.form.get("full_name", "").strip() or "SmartBench User"

    if not email:
        flash("Email is required", "error")
        return render_template("auth/login.html"), 400

    user = AuthService.get_or_create_user(db.session, email=email, full_name=full_name)
    login_user(user)

    workspace = db.session.query(Workspace).order_by(Workspace.created_at.asc()).first()
    if workspace:
        session["active_workspace_id"] = str(workspace.id)

    return redirect(url_for("dashboard.index"))


@bp.post("/logout")
@login_required
def logout() -> object:
    logout_user()
    session.pop("active_workspace_id", None)
    return redirect(url_for("auth.login"))
