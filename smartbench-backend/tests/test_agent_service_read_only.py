from __future__ import annotations

from app.models import AgentActionLog, AgentSession, AuditEvent
from app.services.agent_service import AgentService


def test_agent_prompt_does_not_write_logs_or_audit(session, identity):
    agent_session = AgentSession(
        workspace_id=identity.workspace_id,
        user_id=identity.user_id,
        session_label="Read Only Session",
        created_by=identity.user_id,
        updated_by=identity.user_id,
    )
    session.add(agent_session)
    session.commit()

    service = AgentService()
    result = service.run_prompt(
        session,
        workspace_id=identity.workspace_id,
        prompt="Quais schemas eu tenho?",
        identity=identity,
        session_id=agent_session.id,
    )

    assert result.response.session_id == agent_session.id
    assert len(result.response.actions) >= 1

    assert session.query(AgentActionLog).count() == 0
    assert session.query(AuditEvent).filter(AuditEvent.action == "agent.prompt").count() == 0
