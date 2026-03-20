"""Dynamic schema registry services."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Entity, EntityType, EntityTypeField, EntityTypeVersion, Project, ProjectResourceLink
from app.schemas.registry import EntityCreate, EntityTypeCreate, EntityTypeVersionCreate, EntityUpdate
from app.services.audit_service import AuditService
from app.services.exceptions import NotFoundError, ValidationError
from app.utils.request_context import IdentityContext


class RegistryValidationService:
    """Schema validation for entity payloads."""

    @staticmethod
    def _assert_type(value: Any, field_type: str, enum_values: list[str] | None = None) -> bool:
        if field_type == "string":
            return isinstance(value, str)
        if field_type == "number":
            return isinstance(value, int | float) and not isinstance(value, bool)
        if field_type == "boolean":
            return isinstance(value, bool)
        if field_type == "date":
            return isinstance(value, str)
        if field_type == "json":
            json_scalar = dict | list | str | int | float | bool | type(None)
            return isinstance(value, json_scalar)
        if field_type == "entity_ref":
            return isinstance(value, str)
        if field_type == "enum":
            return isinstance(value, str) and enum_values is not None and value in enum_values
        return False

    @classmethod
    def validate_entity_payload(cls, version: EntityTypeVersion, payload: dict[str, Any]) -> None:
        field_map: dict[str, EntityTypeField] = {f.name: f for f in version.fields}
        unknown_fields = [key for key in payload if key not in field_map]
        if unknown_fields:
            raise ValidationError(f"Unknown fields in payload: {unknown_fields}")

        for field in field_map.values():
            value = payload.get(field.name)
            if value is None:
                if field.is_required:
                    raise ValidationError(f"Field '{field.name}' is required")
                continue

            if field.is_array:
                if not isinstance(value, list):
                    raise ValidationError(f"Field '{field.name}' must be an array")
                for item in value:
                    if not cls._assert_type(item, field.field_type, field.enum_values):
                        raise ValidationError(
                            f"Field '{field.name}' has invalid element type for {field.field_type}"
                        )
                continue

            if not cls._assert_type(value, field.field_type, field.enum_values):
                raise ValidationError(f"Field '{field.name}' must match type {field.field_type}")


class RegistryService:
    """Entity type and entity lifecycle service."""

    @staticmethod
    def _build_schema_snapshot(fields: list[dict[str, Any]]) -> dict[str, Any]:
        return {"fields": fields}

    @staticmethod
    def create_entity_type(
        session: Session,
        payload: EntityTypeCreate,
        identity: IdentityContext,
    ) -> EntityType:
        entity_type = EntityType(
            workspace_id=payload.workspace_id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(entity_type)
        session.flush()

        version = EntityTypeVersion(
            entity_type_id=entity_type.id,
            version=1,
            status="active",
            schema_snapshot=RegistryService._build_schema_snapshot(
                [field.model_dump() for field in payload.fields]
            ),
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(version)
        session.flush()

        for field_input in payload.fields:
            field = EntityTypeField(
                entity_type_version_id=version.id,
                name=field_input.name,
                label=field_input.label,
                field_type=field_input.field_type,
                is_required=field_input.is_required,
                is_array=field_input.is_array,
                enum_values=field_input.enum_values,
                relationship_target=field_input.relationship_target,
                validations=field_input.validations,
                created_by=identity.user_id,
                updated_by=identity.user_id,
            )
            session.add(field)

        entity_type.active_version_id = version.id

        AuditService.record(
            session,
            identity,
            action="entity_type.create",
            target_type="entity_type",
            target_id=entity_type.id,
            payload={"name": entity_type.name, "version": 1},
        )
        session.commit()
        return entity_type

    @staticmethod
    def create_entity_type_version(
        session: Session,
        payload: EntityTypeVersionCreate,
        identity: IdentityContext,
    ) -> EntityTypeVersion:
        entity_type = session.get(EntityType, payload.entity_type_id)
        if entity_type is None:
            raise NotFoundError("Entity type not found")

        latest_version = session.scalar(
            select(EntityTypeVersion)
            .where(EntityTypeVersion.entity_type_id == payload.entity_type_id)
            .order_by(EntityTypeVersion.version.desc())
            .limit(1)
        )
        next_version = 1 if latest_version is None else latest_version.version + 1

        version = EntityTypeVersion(
            entity_type_id=payload.entity_type_id,
            version=next_version,
            status=payload.status,
            schema_snapshot=RegistryService._build_schema_snapshot(
                [field.model_dump() for field in payload.fields]
            ),
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(version)
        session.flush()

        for field_input in payload.fields:
            session.add(
                EntityTypeField(
                    entity_type_version_id=version.id,
                    name=field_input.name,
                    label=field_input.label,
                    field_type=field_input.field_type,
                    is_required=field_input.is_required,
                    is_array=field_input.is_array,
                    enum_values=field_input.enum_values,
                    relationship_target=field_input.relationship_target,
                    validations=field_input.validations,
                    created_by=identity.user_id,
                    updated_by=identity.user_id,
                )
            )

        if payload.status == "active":
            entity_type.active_version_id = version.id

        AuditService.record(
            session,
            identity,
            action="entity_type.version.create",
            target_type="entity_type_version",
            target_id=version.id,
            payload={"entity_type_id": str(entity_type.id), "version": version.version},
        )
        session.commit()
        return version

    @staticmethod
    def get_active_entity_type_version(session: Session, entity_type_id: uuid.UUID) -> EntityTypeVersion:
        entity_type = session.get(EntityType, entity_type_id)
        if entity_type is None:
            raise NotFoundError("Entity type not found")
        if entity_type.active_version_id is None:
            raise ValidationError("Entity type has no active version")

        version = session.get(EntityTypeVersion, entity_type.active_version_id)
        if version is None:
            raise NotFoundError("Active version not found")
        return version

    @staticmethod
    def create_entity(session: Session, payload: EntityCreate, identity: IdentityContext) -> Entity:
        version = RegistryService.get_active_entity_type_version(session, payload.entity_type_id)
        RegistryValidationService.validate_entity_payload(version, payload.data)

        entity = Entity(
            workspace_id=payload.workspace_id,
            entity_type_id=payload.entity_type_id,
            entity_type_version_id=version.id,
            external_id=payload.external_id,
            name=payload.name,
            status=payload.status,
            data=payload.data,
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(entity)

        AuditService.record(
            session,
            identity,
            action="entity.create",
            target_type="entity",
            target_id=entity.id,
            payload={"external_id": entity.external_id, "entity_type_id": str(entity.entity_type_id)},
        )
        session.commit()
        return entity

    @staticmethod
    def update_entity(
        session: Session,
        entity_id: uuid.UUID,
        payload: EntityUpdate,
        identity: IdentityContext,
    ) -> Entity:
        entity = session.get(Entity, entity_id)
        if entity is None:
            raise NotFoundError("Entity not found")

        if payload.name is not None:
            entity.name = payload.name
        if payload.status is not None:
            entity.status = payload.status
        if payload.data is not None:
            version = session.get(EntityTypeVersion, entity.entity_type_version_id)
            if version is None:
                raise NotFoundError("Entity type version not found")
            RegistryValidationService.validate_entity_payload(version, payload.data)
            entity.data = payload.data

        entity.updated_by = identity.user_id

        AuditService.record(
            session,
            identity,
            action="entity.update",
            target_type="entity",
            target_id=entity.id,
            payload=payload.model_dump(exclude_none=True),
        )
        session.commit()
        return entity

    @staticmethod
    def list_entity_types(session: Session, workspace_id: uuid.UUID) -> list[EntityType]:
        stmt = select(EntityType).where(EntityType.workspace_id == workspace_id).order_by(EntityType.name)
        return list(session.scalars(stmt).all())

    @staticmethod
    def list_entities(session: Session, workspace_id: uuid.UUID) -> list[Entity]:
        stmt = select(Entity).where(Entity.workspace_id == workspace_id).order_by(Entity.created_at.desc())
        return list(session.scalars(stmt).all())

    @staticmethod
    def get_entity(session: Session, entity_id: uuid.UUID) -> Entity:
        entity = session.get(Entity, entity_id)
        if entity is None:
            raise NotFoundError("Entity not found")
        return entity

    @staticmethod
    def search_entities(session: Session, workspace_id: uuid.UUID, query: str) -> list[Entity]:
        stmt = (
            select(Entity)
            .where(Entity.workspace_id == workspace_id)
            .where((Entity.name.ilike(f"%{query}%")) | (Entity.external_id.ilike(f"%{query}%")))
            .order_by(Entity.name)
            .limit(50)
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def count_entities_by_type(
        session: Session,
        workspace_id: uuid.UUID,
        *,
        entity_type_id: uuid.UUID | None = None,
        entity_type_slug: str | None = None,
        project_id: uuid.UUID | None = None,
    ) -> tuple[EntityType | None, int, Project | None]:
        stmt = select(EntityType).where(EntityType.workspace_id == workspace_id)
        entity_type: EntityType | None = None
        project: Project | None = None

        if entity_type_id is not None:
            stmt = stmt.where(EntityType.id == entity_type_id)
            entity_type = session.scalar(stmt.limit(1))
        elif entity_type_slug:
            stmt = stmt.where(EntityType.slug == entity_type_slug)
            entity_type = session.scalar(stmt.limit(1))

        if (entity_type_id is not None or entity_type_slug is not None) and entity_type is None:
            raise NotFoundError("Entity type not found in workspace")

        count_stmt = select(func.count(Entity.id)).where(Entity.workspace_id == workspace_id)
        if entity_type is not None:
            count_stmt = count_stmt.where(Entity.entity_type_id == entity_type.id)

        if project_id is not None:
            project = session.scalar(
                select(Project).where(Project.id == project_id).where(Project.workspace_id == workspace_id).limit(1)
            )
            if project is None:
                raise NotFoundError("Project not found in workspace")

            linked_entity_ids = [
                parsed_id
                for raw_id in session.scalars(
                    select(ProjectResourceLink.resource_id)
                    .where(ProjectResourceLink.workspace_id == workspace_id)
                    .where(ProjectResourceLink.project_id == project.id)
                    .where(ProjectResourceLink.resource_type == "entity")
                ).all()
                for parsed_id in [RegistryService._safe_uuid(raw_id)]
                if parsed_id is not None
            ]
            if not linked_entity_ids:
                return entity_type, 0, project
            count_stmt = count_stmt.where(Entity.id.in_(linked_entity_ids))

        total = session.scalar(count_stmt)
        return entity_type, int(total or 0), project

    @staticmethod
    def _safe_uuid(raw_id: str) -> uuid.UUID | None:
        try:
            return uuid.UUID(raw_id)
        except ValueError:
            return None
