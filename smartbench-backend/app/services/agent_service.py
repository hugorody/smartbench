"""Scientific Copilot orchestration service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models import AgentSession
from app.schemas.agents import AgentPromptResponse, AgentToolAction
from app.services.introspection_service import IntrospectionService
from app.services.openai_service import OpenAIService
from app.tools.tool_registry import AgentToolRegistry
from app.utils.request_context import IdentityContext


@dataclass(slots=True)
class AgentExecutionResult:
    response: AgentPromptResponse


class AgentService:
    """Coordinates OpenAI + governed tool calls + action auditability."""

    def __init__(self) -> None:
        self.openai = OpenAIService()
        self.tools = AgentToolRegistry()

    def _resolve_session_id(
        self,
        session: Session,
        *,
        workspace_id: uuid.UUID,
        session_id: uuid.UUID | None,
    ) -> uuid.UUID:
        if session_id is None:
            return uuid.uuid4()

        existing = session.get(AgentSession, session_id)
        if existing is not None and existing.workspace_id == workspace_id:
            return existing.id

        # Read-only policy: do not create or mutate session state in DB during prompts.
        return session_id

    def _heuristic_tool_selection(self, prompt: str) -> list[tuple[str, dict[str, Any]]]:
        lowered = prompt.lower()
        if any(term in lowered for term in ["schema", "schemas", "esquema", "esquemas"]):
            if any(term in lowered for term in ["resultado", "result"]):
                return [("list_result_schemas", {})]
            if any(term in lowered for term in ["entity type", "entidade", "entity", "registry"]):
                return [("list_entity_types", {})]
            return [("list_entity_types", {}), ("list_result_schemas", {})]
        if lowered.startswith("find ") or "search" in lowered:
            q = prompt.replace("find", "").replace("search", "").strip() or prompt
            return [("search_entities", {"query": q})]
        return []

    @staticmethod
    def _format_tool_response(actions: list[AgentToolAction]) -> tuple[str, list[dict[str, Any]]]:
        if not actions:
            return (
                "Nenhuma acao de ferramenta foi executada. "
                "Tente pedir explicitamente para listar schemas, buscar entidades ou consultar workflows.",
                [],
            )

        references: list[dict[str, Any]] = []
        sections: list[str] = []

        for action in actions:
            output = action.output or {}
            if action.tool_name == "list_entity_types":
                entity_types = output.get("entity_types", [])
                sections.append(f"Schemas de entidade encontrados: {len(entity_types)}")
                if entity_types:
                    sections.extend([f"- {item.get('name', 'sem_nome')}" for item in entity_types])
                for item in entity_types:
                    references.append(
                        {
                            "type": "entity_type",
                            "id": item.get("id"),
                            "name": item.get("name"),
                        }
                    )
                continue

            if action.tool_name == "list_result_schemas":
                schemas = output.get("schemas", [])
                sections.append(f"Schemas de resultado encontrados: {len(schemas)}")
                if schemas:
                    sections.extend([f"- {item.get('name', 'sem_nome')}" for item in schemas])
                for item in schemas:
                    references.append(
                        {
                            "type": "result_schema",
                            "id": item.get("id"),
                            "name": item.get("name"),
                        }
                    )
                continue

            if action.tool_name == "search_entities":
                entities = output.get("entities", [])
                sections.append(f"Entidades encontradas: {len(entities)}")
                for item in entities[:15]:
                    sections.append(f"- {item.get('name', 'sem_nome')} ({item.get('external_id', '-')})")
                    references.append(
                        {
                            "type": "entity",
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "external_id": item.get("external_id"),
                        }
                    )
                continue

            sections.append(
                f"Ferramenta {action.tool_name} executada com status {action.status}."
            )

        if not sections:
            sections.append("Ferramentas executadas com sucesso.")

        sections.append("Obs: o agente opera em modo somente leitura para dados da plataforma.")
        return "\n".join(sections), references

    def run_prompt(
        self,
        session: Session,
        *,
        workspace_id: uuid.UUID,
        prompt: str,
        identity: IdentityContext,
        session_id: uuid.UUID | None = None,
    ) -> AgentExecutionResult:
        resolved_session_id = self._resolve_session_id(
            session,
            workspace_id=workspace_id,
            session_id=session_id,
        )

        schema_context = {
            "entity_types": IntrospectionService.entity_types(session, workspace_id),
            "result_schemas": IntrospectionService.result_schemas(session, workspace_id),
            "notebook_templates": IntrospectionService.notebook_templates(session, workspace_id),
            "workflows": IntrospectionService.workflows(session, workspace_id),
        }

        selected_tools = self._heuristic_tool_selection(prompt)
        actions: list[AgentToolAction] = []

        if selected_tools:
            for selected_tool, initial_args in selected_tools:
                tool_args = {"workspace_id": str(workspace_id), **initial_args}
                tool_output = self.tools.dispatch(selected_tool, session, tool_args)
                actions.append(
                    AgentToolAction(
                        tool_name=selected_tool,
                        input=tool_args,
                        output=tool_output,
                        status="success" if "error" not in tool_output else "error",
                    )
                )
            response_text, references = self._format_tool_response(actions)
        else:
            ai_response = self.openai.create_response(
                model="gpt-4.1-mini",
                input_text=(
                    "You are SmartBench Scientific Copilot. "
                    "You operate in read-only mode: never mutate records or suggest direct DB writes. "
                    "Use schema context and do not invent records.\n"
                    f"Schema context: {schema_context}\nUser prompt: {prompt}"
                ),
                tools=self.tools.json_schemas,
                metadata={
                    "workspace_id": str(workspace_id),
                    "agent_session_id": str(resolved_session_id),
                    "actor_user_id": str(identity.user_id or ""),
                },
            )
            response_text = ai_response.get("output_text", "No response generated.")
            references = []

        response = AgentPromptResponse(
            session_id=resolved_session_id,
            response_text=response_text,
            actions=actions,
            references=references,
        )
        return AgentExecutionResult(response=response)
