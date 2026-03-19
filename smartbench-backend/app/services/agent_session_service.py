"""Agent session lifecycle operations."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentSession
from app.services.audit_service import AuditService
from app.services.exceptions import NotFoundError, ValidationError
from app.utils.request_context import IdentityContext


class AgentSessionService:
    """Manage session labels and retention for scientific copilot chats."""

    @staticmethod
    def list_sessions(session: Session, workspace_id: uuid.UUID) -> list[AgentSession]:
        stmt = (
            select(AgentSession)
            .where(AgentSession.workspace_id == workspace_id)
            .order_by(AgentSession.updated_at.desc())
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def get_session(session: Session, workspace_id: uuid.UUID, session_id: uuid.UUID) -> AgentSession:
        agent_session = session.scalar(
            select(AgentSession)
            .where(AgentSession.workspace_id == workspace_id)
            .where(AgentSession.id == session_id)
            .limit(1)
        )
        if agent_session is None:
            raise NotFoundError("Conversation not found in current workspace")
        return agent_session

    @staticmethod
    def rename_session(
        session: Session,
        *,
        workspace_id: uuid.UUID,
        session_id: uuid.UUID,
        new_label: str,
        identity: IdentityContext,
    ) -> AgentSession:
        normalized = new_label.strip()
        if not normalized:
            raise ValidationError("Conversation name cannot be empty")
        if len(normalized) > 255:
            raise ValidationError("Conversation name must be at most 255 characters")

        agent_session = AgentSessionService.get_session(session, workspace_id, session_id)
        old_label = agent_session.session_label or "Scientific Copilot Session"
        agent_session.session_label = normalized
        agent_session.updated_by = identity.user_id

        AuditService.record(
            session,
            identity,
            action="agent_session.rename",
            target_type="agent_session",
            target_id=agent_session.id,
            payload={"old_label": old_label, "new_label": normalized},
        )
        session.commit()
        return agent_session

    @staticmethod
    def delete_session(
        session: Session,
        *,
        workspace_id: uuid.UUID,
        session_id: uuid.UUID,
        identity: IdentityContext,
    ) -> None:
        agent_session = AgentSessionService.get_session(session, workspace_id, session_id)

        AuditService.record(
            session,
            identity,
            action="agent_session.delete",
            target_type="agent_session",
            target_id=agent_session.id,
            payload={"session_label": agent_session.session_label},
        )

        session.delete(agent_session)
        session.commit()
