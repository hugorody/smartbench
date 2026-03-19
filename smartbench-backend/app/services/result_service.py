"""Result schema and records services."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ResultRecord, ResultSchema, ResultSchemaField
from app.schemas.results import ResultRecordCreate, ResultSchemaCreate
from app.services.audit_service import AuditService
from app.services.exceptions import NotFoundError, ValidationError
from app.utils.request_context import IdentityContext


class ResultValidationService:
    """Validates result records against dynamic result schema fields."""

    @staticmethod
    def _field_matches(value: Any, field_type: str, enum_values: list[str] | None) -> bool:
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
        if field_type == "enum":
            return isinstance(value, str) and enum_values is not None and value in enum_values
        return False

    @classmethod
    def validate_record_payload(cls, schema: ResultSchema, payload: dict[str, Any]) -> None:
        field_map = {field.name: field for field in schema.fields}
        unknown = [name for name in payload if name not in field_map]
        if unknown:
            raise ValidationError(f"Unknown result fields: {unknown}")

        for field in schema.fields:
            value = payload.get(field.name)
            if value is None:
                if field.is_required:
                    raise ValidationError(f"Field '{field.name}' is required")
                continue
            if not cls._field_matches(value, field.field_type, field.enum_values):
                raise ValidationError(f"Field '{field.name}' must match type {field.field_type}")


class ResultService:
    """Result schema and record lifecycle operations."""

    @staticmethod
    def create_schema(
        session: Session,
        payload: ResultSchemaCreate,
        identity: IdentityContext,
    ) -> ResultSchema:
        schema = ResultSchema(
            workspace_id=payload.workspace_id,
            name=payload.name,
            description=payload.description,
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(schema)
        session.flush()

        for field in payload.fields:
            session.add(
                ResultSchemaField(
                    result_schema_id=schema.id,
                    name=field.name,
                    label=field.label,
                    field_type=field.field_type,
                    is_required=field.is_required,
                    enum_values=field.enum_values,
                    validations=field.validations,
                    created_by=identity.user_id,
                    updated_by=identity.user_id,
                )
            )

        AuditService.record(
            session,
            identity,
            action="result_schema.create",
            target_type="result_schema",
            target_id=schema.id,
            payload={"name": schema.name},
        )
        session.commit()
        return schema

    @staticmethod
    def create_record(
        session: Session,
        payload: ResultRecordCreate,
        identity: IdentityContext,
    ) -> ResultRecord:
        schema = session.get(ResultSchema, payload.result_schema_id)
        if schema is None:
            raise NotFoundError("Result schema not found")

        ResultValidationService.validate_record_payload(schema, payload.data)

        record = ResultRecord(
            workspace_id=payload.workspace_id,
            result_schema_id=payload.result_schema_id,
            record_key=payload.record_key,
            data=payload.data,
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(record)

        AuditService.record(
            session,
            identity,
            action="result_record.create",
            target_type="result_record",
            target_id=record.id,
            payload={"record_key": record.record_key},
        )
        session.commit()
        return record

    @staticmethod
    def list_schemas(session: Session, workspace_id: uuid.UUID) -> list[ResultSchema]:
        stmt = select(ResultSchema).where(ResultSchema.workspace_id == workspace_id).order_by(ResultSchema.name)
        return list(session.scalars(stmt).all())

    @staticmethod
    def list_records(session: Session, workspace_id: uuid.UUID) -> list[ResultRecord]:
        stmt = (
            select(ResultRecord)
            .where(ResultRecord.workspace_id == workspace_id)
            .order_by(ResultRecord.created_at.desc())
        )
        return list(session.scalars(stmt).all())
