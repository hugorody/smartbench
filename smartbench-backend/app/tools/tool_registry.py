"""Governed internal tool registry used by agent orchestrator."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from app.services.introspection_service import IntrospectionService
from app.services.notebook_service import NotebookService
from app.services.registry_service import RegistryService
from app.services.result_service import ResultService
from app.services.workflow_service import WorkflowService

ToolFn = Callable[..., dict[str, Any]]


class AgentToolRegistry:
    """Tool catalog and dispatcher with stable, auditable names."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {
            "list_entity_types": self.list_entity_types,
            "search_entities": self.search_entities,
            "get_entity": self.get_entity,
            "list_notebook_templates": self.list_notebook_templates,
            "list_result_schemas": self.list_result_schemas,
            "list_workflows": self.list_workflows,
        }

    @property
    def json_schemas(self) -> list[dict[str, Any]]:
        return [
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
        ]

    def dispatch(self, tool_name: str, session: Any, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name not in self._tools:
            return {"error": f"Unsupported tool '{tool_name}'"}
        return self._tools[tool_name](session, **arguments)

    @staticmethod
    def list_entity_types(session: Any, workspace_id: str) -> dict[str, Any]:
        payload = IntrospectionService.entity_types(session, uuid.UUID(workspace_id))
        return {"entity_types": payload}

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
    def list_workflows(session: Any, workspace_id: str) -> dict[str, Any]:
        workflows = WorkflowService.list_definitions(session, uuid.UUID(workspace_id))
        return {
            "workflows": [{"id": str(workflow.id), "name": workflow.name} for workflow in workflows]
        }
