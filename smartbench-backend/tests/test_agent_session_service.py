from __future__ import annotations

from app.models import AgentSession, AuditEvent
from app.services.agent_session_service import AgentSessionService


def test_rename_agent_session_updates_label_and_audit(session, identity):
    agent_session = AgentSession(
        workspace_id=identity.workspace_id,
        user_id=identity.user_id,
        session_label="Old Name",
        created_by=identity.user_id,
        updated_by=identity.user_id,
    )
    session.add(agent_session)
    session.commit()

    renamed = AgentSessionService.rename_session(
        session,
        workspace_id=identity.workspace_id,
        session_id=agent_session.id,
        new_label="Genome Review Thread",
        identity=identity,
    )

    assert renamed.session_label == "Genome Review Thread"

    event = session.query(AuditEvent).filter_by(action="agent_session.rename").one()
    assert event.target_id == str(agent_session.id)
    assert event.payload["new_label"] == "Genome Review Thread"


def test_delete_agent_session_removes_record_and_writes_audit(session, identity):
    agent_session = AgentSession(
        workspace_id=identity.workspace_id,
        user_id=identity.user_id,
        session_label="Disposable Thread",
        created_by=identity.user_id,
        updated_by=identity.user_id,
    )
    session.add(agent_session)
    session.commit()

    AgentSessionService.delete_session(
        session,
        workspace_id=identity.workspace_id,
        session_id=agent_session.id,
        identity=identity,
    )

    assert session.get(AgentSession, agent_session.id) is None

    event = session.query(AuditEvent).filter_by(action="agent_session.delete").one()
    assert event.target_id == str(agent_session.id)
