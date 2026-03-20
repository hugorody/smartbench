"""Governed internal tool registry used by agent orchestrator."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from app.services.agent_analytics_service import AgentAnalyticsService
from app.services.introspection_service import IntrospectionService
from app.services.notebook_service import NotebookService
from app.services.project_service import ProjectService
from app.services.registry_service import RegistryService
from app.services.result_service import ResultService
from app.services.workflow_service import WorkflowService

ToolFn = Callable[..., dict[str, Any]]


class AgentToolRegistry:
    """Tool catalog and dispatcher with stable, auditable names."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {
            "list_projects": self.list_projects,
            "workspace_overview_counts": self.workspace_overview_counts,
            "list_entity_types": self.list_entity_types,
            "count_entities": self.count_entities,
            "search_entities": self.search_entities,
            "get_entity": self.get_entity,
            "list_notebook_templates": self.list_notebook_templates,
            "list_result_schemas": self.list_result_schemas,
            "result_numeric_stats": self.result_numeric_stats,
            "list_workflows": self.list_workflows,
        }

    @property
    def json_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": "list_projects",
                "description": "List projects in a workspace",
                "parameters": {
                    "type": "object",
                    "properties": {"workspace_id": {"type": "string"}},
                    "required": ["workspace_id"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "workspace_overview_counts",
                "description": "Return resource counts for workspace or project scope",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "workspace_id": {"type": "string"},
                        "project_id": {"type": "string"},
                    },
                    "required": ["workspace_id"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "list_entity_types",
                "description": "List available dynamic entity types in a workspace",
                "parameters": {
                    "type": "object",
                    "properties": {"workspace_id": {"type": "string"}},
                    "required": ["workspace_id"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "count_entities",
                "description": "Count registered entities by optional type and optional project scope",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "workspace_id": {"type": "string"},
                        "entity_type_id": {"type": "string"},
                        "entity_type_slug": {"type": "string"},
                        "project_id": {"type": "string"},
                    },
                    "required": ["workspace_id"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "search_entities",
                "description": "Search entities by id or name fragment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "workspace_id": {"type": "string"},
                        "query": {"type": "string"},
                    },
                    "required": ["workspace_id", "query"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "get_entity",
                "description": "Get an entity by ID",
                "parameters": {
                    "type": "object",
                    "properties": {"entity_id": {"type": "string"}},
                    "required": ["entity_id"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "list_notebook_templates",
                "description": "List notebook templates in a workspace",
                "parameters": {
                    "type": "object",
                    "properties": {"workspace_id": {"type": "string"}},
                    "required": ["workspace_id"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "list_result_schemas",
                "description": "List result schemas in a workspace",
                "parameters": {
                    "type": "object",
                    "properties": {"workspace_id": {"type": "string"}},
                    "required": ["workspace_id"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "result_numeric_stats",
                "description": "Compute descriptive statistics across numeric result fields",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "workspace_id": {"type": "string"},
                        "schema_id": {"type": "string"},
                        "project_id": {"type": "string"},
                    },
                    "required": ["workspace_id"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "list_workflows",
                "description": "List workflows in a workspace",
                "parameters": {
                    "type": "object",
                    "properties": {"workspace_id": {"type": "string"}},
                    "required": ["workspace_id"],
                    "additionalProperties": False,
                },
            },
        ]

    def dispatch(self, tool_name: str, session: Any, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name not in self._tools:
            return {"error": f"Unsupported tool '{tool_name}'"}
        return self._tools[tool_name](session, **arguments)

    @staticmethod
    def list_projects(session: Any, workspace_id: str) -> dict[str, Any]:
        projects = ProjectService.list_projects(session, uuid.UUID(workspace_id))
        return {
            "projects": [
                {
                    "id": str(project.id),
                    "name": project.name,
                    "description": project.description,
                }
                for project in projects
            ]
        }

    @staticmethod
    def workspace_overview_counts(session: Any, workspace_id: str, project_id: str | None = None) -> dict[str, Any]:
        parsed_project_id = uuid.UUID(project_id) if project_id else None
        return AgentAnalyticsService.workspace_overview_counts(
            session,
            uuid.UUID(workspace_id),
            project_id=parsed_project_id,
        )

    @staticmethod
    def list_entity_types(session: Any, workspace_id: str) -> dict[str, Any]:
        payload = IntrospectionService.entity_types(session, uuid.UUID(workspace_id))
        return {"entity_types": payload}

    @staticmethod
    def count_entities(
        session: Any,
        workspace_id: str,
        entity_type_id: str | None = None,
        entity_type_slug: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        parsed_entity_type_id = uuid.UUID(entity_type_id) if entity_type_id else None
        parsed_project_id = uuid.UUID(project_id) if project_id else None
        entity_type, total, project = RegistryService.count_entities_by_type(
            session,
            uuid.UUID(workspace_id),
            entity_type_id=parsed_entity_type_id,
            entity_type_slug=entity_type_slug,
            project_id=parsed_project_id,
        )
        return {
            "count": total,
            "entity_type": (
                {
                    "id": str(entity_type.id),
                    "name": entity_type.name,
                    "slug": entity_type.slug,
                }
                if entity_type is not None
                else None
            ),
            "project": (
                {
                    "id": str(project.id),
                    "name": project.name,
                }
                if project is not None
                else None
            ),
        }

    @staticmethod
    def search_entities(session: Any, workspace_id: str, query: str) -> dict[str, Any]:
        entities = RegistryService.search_entities(session, uuid.UUID(workspace_id), query)
        return {
            "entities": [
                {
                    "id": str(entity.id),
                    "external_id": entity.external_id,
                    "name": entity.name,
                    "status": entity.status,
                }
                for entity in entities
            ]
        }

    @staticmethod
    def get_entity(session: Any, entity_id: str) -> dict[str, Any]:
        entity = RegistryService.get_entity(session, uuid.UUID(entity_id))
        return {
            "entity": {
                "id": str(entity.id),
                "external_id": entity.external_id,
                "name": entity.name,
                "status": entity.status,
                "data": entity.data,
            }
        }

    @staticmethod
    def list_notebook_templates(session: Any, workspace_id: str) -> dict[str, Any]:
        templates = NotebookService.list_templates(session, uuid.UUID(workspace_id))
        return {
            "templates": [{"id": str(template.id), "name": template.name} for template in templates]
        }

    @staticmethod
    def list_result_schemas(session: Any, workspace_id: str) -> dict[str, Any]:
        schemas = ResultService.list_schemas(session, uuid.UUID(workspace_id))
        return {"schemas": [{"id": str(schema.id), "name": schema.name} for schema in schemas]}

    @staticmethod
    def result_numeric_stats(
        session: Any,
        workspace_id: str,
        schema_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        parsed_schema_id = uuid.UUID(schema_id) if schema_id else None
        parsed_project_id = uuid.UUID(project_id) if project_id else None
        return AgentAnalyticsService.result_numeric_stats(
            session,
            uuid.UUID(workspace_id),
            schema_id=parsed_schema_id,
            project_id=parsed_project_id,
        )

    @staticmethod
    def list_workflows(session: Any, workspace_id: str) -> dict[str, Any]:
        workflows = WorkflowService.list_definitions(session, uuid.UUID(workspace_id))
        return {
            "workflows": [{"id": str(workflow.id), "name": workflow.name} for workflow in workflows]
        }
