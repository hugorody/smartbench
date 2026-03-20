"""Scientific Copilot orchestration service."""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models import AgentActionLog, AgentSession
from app.schemas.agents import AgentPromptResponse, AgentToolAction
from app.services.exceptions import ValidationError
from app.services.introspection_service import IntrospectionService
from app.services.openai_service import OpenAIService
from app.services.project_service import ProjectService
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

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        lowered = without_accents.lower()
        return re.sub(r"[^a-z0-9\s_-]+", " ", lowered).strip()

    @classmethod
    def _extract_entity_type_for_count(
        cls,
        prompt: str,
        entity_types: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        normalized_prompt = cls._normalize_text(prompt)
        for entity_type in entity_types:
            name = cls._normalize_text(entity_type.get("name", ""))
            slug = cls._normalize_text(entity_type.get("slug", ""))
            variants = {name, slug}
            for token in [name, slug]:
                if not token:
                    continue
                variants.add(token.rstrip("s"))
                variants.add(f"{token}s")
                variants.add(f"{token}es")
            if any(variant and variant in normalized_prompt for variant in variants):
                return entity_type
        return None

    @classmethod
    def _extract_result_schema(
        cls,
        prompt: str,
        schemas: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        normalized_prompt = cls._normalize_text(prompt)
        for schema in schemas:
            normalized_name = cls._normalize_text(schema.get("name", ""))
            if normalized_name and normalized_name in normalized_prompt:
                return schema
        return None

    @classmethod
    def _extract_project_from_prompt(
        cls,
        prompt: str,
        projects: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        normalized_prompt = cls._normalize_text(prompt)
        indexed_match = re.search(r"\b(?:projeto|project)\s+(\d+)\b", normalized_prompt)
        if indexed_match:
            index = int(indexed_match.group(1))
            if 1 <= index <= len(projects):
                return projects[index - 1]

        for project in projects:
            normalized_name = cls._normalize_text(project.get("name", ""))
            if normalized_name and normalized_name in normalized_prompt:
                return project
        return None

    def _resolve_session_id(
        self,
        session: Session,
        *,
        workspace_id: uuid.UUID,
        session_id: uuid.UUID | None,
        identity: IdentityContext,
    ) -> uuid.UUID:
        if session_id is None:
            created = AgentSession(
                workspace_id=workspace_id,
                user_id=identity.user_id,
                session_label="Scientific Copilot Session",
                status="active",
                created_by=identity.user_id,
                updated_by=identity.user_id,
            )
            session.add(created)
            session.flush()
            return created.id

        existing = session.get(AgentSession, session_id)
        if existing is not None and existing.workspace_id == workspace_id:
            return existing.id

        raise ValidationError("Agent session does not exist in the selected workspace")

    @staticmethod
    def _record_action(
        session: Session,
        *,
        workspace_id: uuid.UUID,
        session_id: uuid.UUID,
        identity: IdentityContext,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: dict[str, Any] | None,
        status: str,
        error_message: str | None = None,
    ) -> None:
        session.add(
            AgentActionLog(
                workspace_id=workspace_id,
                agent_session_id=session_id,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=tool_output,
                status=status,
                error_message=error_message,
                created_by=identity.user_id,
                updated_by=identity.user_id,
            )
        )

    def _heuristic_tool_selection(
        self,
        prompt: str,
        *,
        workspace_id: uuid.UUID,
        session: Session,
    ) -> list[tuple[str, dict[str, Any]]]:
        normalized = self._normalize_text(prompt)
        lowered = prompt.lower()

        entity_types = IntrospectionService.entity_types(session, workspace_id)
        result_schemas = IntrospectionService.result_schemas(session, workspace_id)
        projects = [
            {"id": str(project.id), "name": project.name}
            for project in ProjectService.list_projects(session, workspace_id)
        ]

        matched_entity_type = self._extract_entity_type_for_count(prompt, entity_types)
        matched_project = self._extract_project_from_prompt(prompt, projects)
        matched_schema = self._extract_result_schema(prompt, result_schemas)

        count_terms = [
            "quantos",
            "quantas",
            "how many",
            "count",
            "numero",
            "algum",
            "alguma",
            "existe",
            "ha",
            "tem",
        ]
        stats_terms = [
            "estatistica",
            "estatisticas",
            "analise",
            "media",
            "mean",
            "desvio",
            "variancia",
            "distribuicao",
            "histograma",
        ]

        has_count_intent = any(term in normalized for term in count_terms)
        has_stats_intent = any(term in normalized for term in stats_terms)

        if has_count_intent and (matched_entity_type is not None or "entidad" in normalized or "entity" in normalized):
            args: dict[str, Any] = {}
            if matched_entity_type is not None:
                args["entity_type_id"] = matched_entity_type.get("id")
            if matched_project is not None:
                args["project_id"] = matched_project.get("id")
            return [("count_entities", args)]

        if has_count_intent and (
            "projeto" in normalized
            or "project" in normalized
            or "plataforma" in normalized
            or "workspace" in normalized
        ):
            args = {}
            if matched_project is not None:
                args["project_id"] = matched_project.get("id")
            return [("workspace_overview_counts", args)]

        if has_stats_intent or ("estat" in normalized and ("resultado" in normalized or "result" in normalized)):
            args = {}
            if matched_project is not None:
                args["project_id"] = matched_project.get("id")
            if matched_schema is not None:
                args["schema_id"] = matched_schema.get("id")
            return [("result_numeric_stats", args)]

        if any(term in lowered for term in ["schema", "schemas", "esquema", "esquemas"]):
            if any(term in lowered for term in ["resultado", "result"]):
                return [("list_result_schemas", {})]
            if any(term in lowered for term in ["entity type", "entidade", "entity", "registry"]):
                return [("list_entity_types", {})]
            return [("list_entity_types", {}), ("list_result_schemas", {})]

        if any(term in lowered for term in ["project", "projeto"]) and any(
            term in lowered for term in ["list", "listar", "quais", "which"]
        ):
            return [("list_projects", {})]

        if lowered.startswith("find ") or "search" in lowered or "buscar" in lowered:
            q = prompt.replace("find", "").replace("search", "").replace("buscar", "").strip() or prompt
            return [("search_entities", {"query": q})]

        return []

    @staticmethod
    def _build_table_artifact(title: str, columns: list[str], rows: list[list[Any]]) -> dict[str, Any]:
        return {
            "type": "table",
            "title": title,
            "columns": columns,
            "rows": rows,
        }

    @staticmethod
    def _build_bar_chart_artifact(title: str, labels: list[str], values: list[float]) -> dict[str, Any]:
        return {
            "type": "bar_chart",
            "title": title,
            "labels": labels,
            "values": values,
        }

    def _format_tool_response(
        self,
        actions: list[AgentToolAction],
        *,
        prompt: str,
    ) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
        if not actions:
            return (
                (
                    "Nao consegui identificar uma consulta estruturada para executar. "
                    "Tente pedir uma contagem, resumo de projeto ou analise "
                    "estatistica de resultados."
                ),
                [],
                [],
            )

        normalized_prompt = self._normalize_text(prompt)
        existence_intent = any(term in normalized_prompt for term in ["algum", "alguma", "existe", "ha", "tem"])

        references: list[dict[str, Any]] = []
        sections: list[str] = []
        artifacts: list[dict[str, Any]] = []

        for action in actions:
            output = action.output or {}

            if action.tool_name == "count_entities":
                entity_type = output.get("entity_type") or {}
                project = output.get("project") or {}
                entity_type_name = entity_type.get("name") or "entidades"
                total = int(output.get("count", 0))

                scope_suffix = f" no projeto {project.get('name')}" if project else ""
                if existence_intent:
                    if total > 0:
                        sections.append(f"Sim. Existem {total} registros de {entity_type_name}{scope_suffix}.")
                    else:
                        sections.append(f"Nao. Nao encontrei registros de {entity_type_name}{scope_suffix}.")
                else:
                    sections.append(f"Total de registros de {entity_type_name}{scope_suffix}: {total}.")

                artifacts.append(
                    self._build_table_artifact(
                        "Contagem de Entidades",
                        ["Escopo", "Tipo", "Total"],
                        [[project.get("name") if project else "Workspace", entity_type_name, total]],
                    )
                )
                artifacts.append(
                    self._build_bar_chart_artifact(
                        "Entidades Encontradas",
                        [entity_type_name],
                        [float(total)],
                    )
                )

                if entity_type:
                    references.append(
                        {
                            "type": "entity_type",
                            "id": entity_type.get("id"),
                            "name": entity_type.get("name"),
                            "slug": entity_type.get("slug"),
                        }
                    )
                if project:
                    references.append(
                        {
                            "type": "project",
                            "id": project.get("id"),
                            "name": project.get("name"),
                        }
                    )
                continue

            if action.tool_name == "workspace_overview_counts":
                counts = output.get("counts", {})
                scope = output.get("scope", {})
                project = scope.get("project") or {}
                scope_label = project.get("name") or "Workspace"
                sections.append(
                    "Resumo de recursos: "
                    f"entidades={counts.get('entities', 0)}, notebooks={counts.get('notebook_entries', 0)}, "
                    f"resultados={counts.get('result_records', 0)}, workflows={counts.get('workflow_runs', 0)} "
                    f"(escopo: {scope_label})."
                )

                table_rows = [
                    ["Entities", counts.get("entities", 0)],
                    ["Notebook Entries", counts.get("notebook_entries", 0)],
                    ["Result Records", counts.get("result_records", 0)],
                    ["Workflow Runs", counts.get("workflow_runs", 0)],
                ]
                artifacts.append(
                    self._build_table_artifact(
                        "Resumo de Recursos",
                        ["Recurso", "Total"],
                        table_rows,
                    )
                )
                artifacts.append(
                    self._build_bar_chart_artifact(
                        "Distribuicao de Recursos",
                        [row[0] for row in table_rows],
                        [float(row[1]) for row in table_rows],
                    )
                )

                if project:
                    references.append(
                        {
                            "type": "project",
                            "id": project.get("id"),
                            "name": project.get("name"),
                        }
                    )
                continue

            if action.tool_name == "result_numeric_stats":
                fields = output.get("fields", [])
                record_count = int(output.get("record_count", 0))
                scope = output.get("scope", {})
                schema = scope.get("schema") or {}
                project = scope.get("project") or {}

                if not fields:
                    sections.append("Nao encontrei campos numericos para calcular estatisticas no escopo solicitado.")
                    continue

                sections.append(
                    "Analise estatistica concluida para "
                    f"{record_count} registros com {len(fields)} campo(s) numerico(s)."
                )

                table_rows: list[list[Any]] = []
                for field in fields:
                    table_rows.append(
                        [
                            field.get("field"),
                            field.get("count"),
                            round(float(field.get("min", 0.0)), 4),
                            round(float(field.get("mean", 0.0)), 4),
                            round(float(field.get("max", 0.0)), 4),
                            round(float(field.get("std_dev", 0.0)), 4),
                        ]
                    )

                artifacts.append(
                    self._build_table_artifact(
                        "Estatisticas de Resultados",
                        ["Campo", "N", "Min", "Media", "Max", "DesvioPadrao"],
                        table_rows,
                    )
                )
                artifacts.append(
                    self._build_bar_chart_artifact(
                        "Medias por Campo",
                        [row[0] for row in table_rows],
                        [float(row[3]) for row in table_rows],
                    )
                )

                if schema:
                    references.append(
                        {
                            "type": "result_schema",
                            "id": schema.get("id"),
                            "name": schema.get("name"),
                        }
                    )
                if project:
                    references.append(
                        {
                            "type": "project",
                            "id": project.get("id"),
                            "name": project.get("name"),
                        }
                    )
                continue

            if action.tool_name == "list_entity_types":
                entity_types = output.get("entity_types", [])
                sections.append(f"Schemas de entidade encontrados: {len(entity_types)}")
                artifacts.append(
                    self._build_table_artifact(
                        "Entity Types",
                        ["Nome", "Slug", "Versao Ativa"],
                        [[item.get("name"), item.get("slug"), item.get("active_version")] for item in entity_types],
                    )
                )
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
                artifacts.append(
                    self._build_table_artifact(
                        "Result Schemas",
                        ["Nome", "ID"],
                        [[item.get("name"), item.get("id")] for item in schemas],
                    )
                )
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
                artifacts.append(
                    self._build_table_artifact(
                        "Entities",
                        ["Nome", "External ID", "Status"],
                        [[item.get("name"), item.get("external_id"), item.get("status")] for item in entities],
                    )
                )
                for item in entities:
                    references.append(
                        {
                            "type": "entity",
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "external_id": item.get("external_id"),
                        }
                    )
                continue

            if action.tool_name == "list_projects":
                projects = output.get("projects", [])
                sections.append(f"Projetos encontrados: {len(projects)}")
                artifacts.append(
                    self._build_table_artifact(
                        "Projects",
                        ["Nome", "Descricao"],
                        [[item.get("name"), item.get("description") or "-"] for item in projects],
                    )
                )
                for item in projects:
                    references.append(
                        {
                            "type": "project",
                            "id": item.get("id"),
                            "name": item.get("name"),
                        }
                    )
                continue

            sections.append(f"Ferramenta {action.tool_name} executada com status {action.status}.")

        if not sections:
            sections.append("Operacao concluida com sucesso.")

        return "\n".join(sections), references, artifacts

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
            identity=identity,
        )

        schema_context = {
            "entity_types": IntrospectionService.entity_types(session, workspace_id),
            "result_schemas": IntrospectionService.result_schemas(session, workspace_id),
            "notebook_templates": IntrospectionService.notebook_templates(session, workspace_id),
            "workflows": IntrospectionService.workflows(session, workspace_id),
        }

        selected_tools = self._heuristic_tool_selection(
            prompt,
            workspace_id=workspace_id,
            session=session,
        )
        actions: list[AgentToolAction] = []
        artifacts: list[dict[str, Any]] = []

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
            response_text, references, artifacts = self._format_tool_response(actions, prompt=prompt)
        else:
            ai_response = self.openai.create_response(
                model="gpt-4.1-mini",
                input_text=(
                    "You are SmartBench Scientific Copilot. "
                    "Never claim that records were created, updated, or deleted. "
                    "If a mutation is requested, explain it cannot be executed in chat. "
                    "Use schema context and do not invent records."
                    f"\nSchema context: {schema_context}\nUser prompt: {prompt}"
                ),
                tools=None,
                metadata={
                    "workspace_id": str(workspace_id),
                    "agent_session_id": str(resolved_session_id),
                    "actor_user_id": str(identity.user_id or ""),
                },
            )
            response_text = (ai_response.get("output_text") or "").strip() or (
                "Nao consegui gerar resposta agora. Tente reformular em uma pergunta objetiva, "
                "por exemplo: 'quantos plasmideos tenho no projeto 1?'."
            )
            references = []

        response = AgentPromptResponse(
            session_id=resolved_session_id,
            response_text=response_text,
            actions=[],
            artifacts=artifacts,
            references=references,
        )

        self._record_action(
            session,
            workspace_id=workspace_id,
            session_id=resolved_session_id,
            identity=identity,
            tool_name="user_prompt",
            tool_input={"prompt": prompt},
            tool_output=None,
            status="success",
        )
        self._record_action(
            session,
            workspace_id=workspace_id,
            session_id=resolved_session_id,
            identity=identity,
            tool_name="assistant_response",
            tool_input={"prompt": prompt},
            tool_output={
                "response_text": response_text,
                "actions": [action.model_dump() for action in actions],
                "artifacts": artifacts,
                "references": references,
            },
            status="success",
        )
        session.commit()

        return AgentExecutionResult(response=response)
