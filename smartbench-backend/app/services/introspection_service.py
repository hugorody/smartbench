"""Schema introspection service for UI and agent context."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EntityType, NotebookTemplate, ResultSchema, WorkflowDefinition


class IntrospectionService:
    """Provides machine-readable dynamic schema descriptions."""

    @staticmethod
    def entity_types(session: Session, workspace_id: uuid.UUID) -> list[dict]:
        types = list(
            session.scalars(
                select(EntityType).where(EntityType.workspace_id == workspace_id).order_by(EntityType.name)
            ).all()
        )
        payload: list[dict] = []
        for entity_type in types:
            version = None
            if entity_type.active_version_id:
                version = next(
                    (v for v in entity_type.versions if v.id == entity_type.active_version_id),
                    None,
                )
            payload.append(
                {
                    "id": str(entity_type.id),
                    "name": entity_type.name,
                    "slug": entity_type.slug,
                    "active_version": version.version if version else None,
                    "fields": [
                        {
                            "name": field.name,
                            "type": field.field_type,
                            "required": field.is_required,
                            "enum_values": field.enum_values,
                        }
                        for field in (version.fields if version else [])
                    ],
                }
            )
        return payload

    @staticmethod
    def result_schemas(session: Session, workspace_id: uuid.UUID) -> list[dict]:
        schemas = list(
            session.scalars(
                select(ResultSchema).where(ResultSchema.workspace_id == workspace_id).order_by(ResultSchema.name)
            ).all()
        )
        return [
            {
                "id": str(schema.id),
                "name": schema.name,
                "fields": [
                    {
                        "name": field.name,
                        "type": field.field_type,
                        "required": field.is_required,
                        "enum_values": field.enum_values,
                    }
                    for field in schema.fields
                ],
            }
            for schema in schemas
        ]

    @staticmethod
    def notebook_templates(session: Session, workspace_id: uuid.UUID) -> list[dict]:
        templates = list(
            session.scalars(
                select(NotebookTemplate)
                .where(NotebookTemplate.workspace_id == workspace_id)
                .order_by(NotebookTemplate.name)
            ).all()
        )
        return [
            {
                "id": str(template.id),
                "name": template.name,
                "sections": [
                    {
                        "name": section.name,
                        "label": section.label,
                        "schema": section.section_schema,
                    }
                    for section in template.sections
                ],
            }
            for template in templates
        ]

    @staticmethod
    def workflows(session: Session, workspace_id: uuid.UUID) -> list[dict]:
        workflows = list(
            session.scalars(
                select(WorkflowDefinition)
                .where(WorkflowDefinition.workspace_id == workspace_id)
                .order_by(WorkflowDefinition.name)
            ).all()
        )
        return [
            {
                "id": str(workflow.id),
                "name": workflow.name,
                "states": [{"name": s.name, "initial": s.is_initial} for s in workflow.states],
                "transitions": [
                    {
                        "name": t.name,
                        "from": t.from_state,
                        "to": t.to_state,
                        "required_fields": t.required_fields,
                    }
                    for t in workflow.transitions
                ],
            }
            for workflow in workflows
        ]
