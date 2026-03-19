"""Semantic serializers for schema-aware retrieval preparation."""

from __future__ import annotations

from app.models import (
    Entity,
    EntityType,
    EntityTypeVersion,
    NotebookEntry,
    NotebookTemplate,
    ResultSchema,
    WorkflowDefinition,
)


class SemanticSerializer:
    """Builds concise, human-readable object summaries."""

    @staticmethod
    def entity_type_summary(entity_type: EntityType, version: EntityTypeVersion) -> str:
        field_names = ", ".join(field.name for field in version.fields)
        return f"EntityType {entity_type.name} (v{version.version}) fields: {field_names}"

    @staticmethod
    def entity_summary(entity: Entity) -> str:
        data_keys = list(entity.data.keys())
        return f"Entity {entity.external_id} ({entity.name}) status={entity.status} data_keys={data_keys}"

    @staticmethod
    def notebook_template_summary(template: NotebookTemplate) -> str:
        section_names = ", ".join(section.name for section in template.sections)
        return f"NotebookTemplate {template.name} sections: {section_names}"

    @staticmethod
    def notebook_entry_summary(entry: NotebookEntry) -> str:
        section_names = ", ".join(section.name for section in entry.sections)
        return f"NotebookEntry {entry.entry_key} title={entry.title} sections: {section_names}"

    @staticmethod
    def result_schema_summary(schema: ResultSchema) -> str:
        field_names = ", ".join(field.name for field in schema.fields)
        return f"ResultSchema {schema.name} fields: {field_names}"

    @staticmethod
    def workflow_summary(definition: WorkflowDefinition) -> str:
        states = ", ".join(state.name for state in definition.states)
        transitions = ", ".join(t.name for t in definition.transitions)
        return f"Workflow {definition.name} states={states} transitions={transitions}"
