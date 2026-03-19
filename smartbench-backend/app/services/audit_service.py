"""Audit event writer."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent
from app.utils.request_context import IdentityContext


class AuditService:
    """Encapsulates immutable audit event persistence."""

    @staticmethod
    def record(
        session: Session,
        identity: IdentityContext,
        action: str,
        target_type: str,
        target_id: str | uuid.UUID,
        payload: dict[str, Any] | None = None,
        outcome: str = "success",
        reason: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            workspace_id=identity.workspace_id,
            actor_user_id=identity.user_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            payload=payload,
            request_source=identity.source,
            outcome=outcome,
            reason=reason,
        )
        session.add(event)
        return event
