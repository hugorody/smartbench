"""Optional Celery scaffold."""

from __future__ import annotations

from celery import Celery
from flask import Flask


def create_celery(app: Flask) -> Celery:
    celery = Celery(app.import_name, broker=app.config["REDIS_URL"], backend=app.config["REDIS_URL"])
    celery.conf.update(app.config)

    class ContextTask(celery.Task):  # type: ignore[misc]
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
