from __future__ import annotations

import uuid

from app.models import (
    AgentActionLog,
    AgentSession,
    AuditEvent,
    Entity,
    EntityType,
    EntityTypeVersion,
    Project,
    ProjectResourceLink,
)
from app.services.agent_service import AgentService


def _create_plasmid_type(session, identity) -> tuple[EntityType, EntityTypeVersion]:
    entity_type = EntityType(
        workspace_id=identity.workspace_id,
        name="Plasmid",
        slug="plasmid",
        created_by=identity.user_id,
        updated_by=identity.user_id,
    )
    session.add(entity_type)
    session.flush()

    version = EntityTypeVersion(
        entity_type_id=entity_type.id,
        version=1,
        status="active",
        schema_snapshot={"fields": []},
        created_by=identity.user_id,
        updated_by=identity.user_id,
    )
    session.add(version)
    session.flush()
    entity_type.active_version_id = version.id
    session.flush()
    return entity_type, version


def test_agent_prompt_persists_chat_messages_without_domain_audit(session, identity):
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
    assert result.response.actions == []
    assert isinstance(result.response.artifacts, list)

    logs = (
        session.query(AgentActionLog)
        .filter(AgentActionLog.agent_session_id == agent_session.id)
        .order_by(AgentActionLog.created_at.asc())
        .all()
    )
    assert [log.tool_name for log in logs] == ["user_prompt", "assistant_response"]
    assert (logs[0].tool_input or {}).get("prompt") == "Quais schemas eu tenho?"
    assert "response_text" in (logs[1].tool_output or {})

    assert session.query(AuditEvent).filter(AuditEvent.action == "agent.prompt").count() == 0


def test_agent_prompt_counts_plasmids_with_governed_tool(session, identity):
    entity_type, version = _create_plasmid_type(session, identity)

    session.add_all(
        [
            Entity(
                workspace_id=identity.workspace_id,
                entity_type_id=entity_type.id,
                entity_type_version_id=version.id,
                external_id=f"PLS-{uuid.uuid4().hex[:6]}",
                name="Plasmid A",
                status="active",
                data={},
                created_by=identity.user_id,
                updated_by=identity.user_id,
            ),
            Entity(
                workspace_id=identity.workspace_id,
                entity_type_id=entity_type.id,
                entity_type_version_id=version.id,
                external_id=f"PLS-{uuid.uuid4().hex[:6]}",
                name="Plasmid B",
                status="active",
                data={},
                created_by=identity.user_id,
                updated_by=identity.user_id,
            ),
        ]
    )
    session.commit()

    agent_session = AgentSession(
        workspace_id=identity.workspace_id,
        user_id=identity.user_id,
        session_label="Count Session",
        created_by=identity.user_id,
        updated_by=identity.user_id,
    )
    session.add(agent_session)
    session.commit()

    service = AgentService()
    result = service.run_prompt(
        session,
        workspace_id=identity.workspace_id,
        prompt="Quantos plasmideos eu tenho registrado?",
        identity=identity,
        session_id=agent_session.id,
    )

    assert "Total de registros de Plasmid" in result.response.response_text
    assert result.response.actions == []
    assert any(artifact.get("type") == "table" for artifact in result.response.artifacts)
    assert any(artifact.get("type") == "bar_chart" for artifact in result.response.artifacts)

    logs = (
        session.query(AgentActionLog)
        .filter(AgentActionLog.agent_session_id == agent_session.id)
        .order_by(AgentActionLog.created_at.asc())
        .all()
    )
    assistant_payload = logs[-1].tool_output or {}
    action_names = [item.get("tool_name") for item in assistant_payload.get("actions", [])]
    assert "count_entities" in action_names


def test_agent_prompt_counts_entities_with_project_scope(session, identity):
    entity_type, version = _create_plasmid_type(session, identity)

    plasmid_in_project = Entity(
        workspace_id=identity.workspace_id,
        entity_type_id=entity_type.id,
        entity_type_version_id=version.id,
        external_id=f"PLS-{uuid.uuid4().hex[:6]}",
        name="Plasmid in Project",
        status="active",
        data={},
        created_by=identity.user_id,
        updated_by=identity.user_id,
    )
    plasmid_outside = Entity(
        workspace_id=identity.workspace_id,
        entity_type_id=entity_type.id,
        entity_type_version_id=version.id,
        external_id=f"PLS-{uuid.uuid4().hex[:6]}",
        name="Plasmid outside Project",
        status="active",
        data={},
        created_by=identity.user_id,
        updated_by=identity.user_id,
    )
    session.add_all([plasmid_in_project, plasmid_outside])
    session.flush()

    project = Project(
        workspace_id=identity.workspace_id,
        name="Projeto de Plasmideos",
        description="Projeto de teste",
        created_by=identity.user_id,
        updated_by=identity.user_id,
    )
    session.add(project)
    session.flush()

    session.add(
        ProjectResourceLink(
            workspace_id=identity.workspace_id,
            project_id=project.id,
            resource_type="entity",
            resource_id=str(plasmid_in_project.id),
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
    )
    session.commit()

    agent_session = AgentSession(
        workspace_id=identity.workspace_id,
        user_id=identity.user_id,
        session_label="Project Count Session",
        created_by=identity.user_id,
        updated_by=identity.user_id,
    )
    session.add(agent_session)
    session.commit()

    service = AgentService()
    result = service.run_prompt(
        session,
        workspace_id=identity.workspace_id,
        prompt="Algum plasmideo no projeto 1?",
        identity=identity,
        session_id=agent_session.id,
    )

    assert "Sim. Existem 1 registros de Plasmid no projeto Projeto de Plasmideos." in result.response.response_text
    assert any(artifact.get("type") == "table" for artifact in result.response.artifacts)
