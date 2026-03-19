"""Shared Flask extensions."""

from __future__ import annotations

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Expire disabled to keep loaded attributes available in service/audit boundaries.
db = SQLAlchemy(session_options={"expire_on_commit": False})
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
