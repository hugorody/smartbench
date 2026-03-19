from __future__ import annotations

import pytest

from app.schemas.results import ResultRecordCreate, ResultSchemaCreate, ResultSchemaFieldInput
from app.services.exceptions import ValidationError
from app.services.result_service import ResultService


def test_result_schema_validation(session, identity):
    schema = ResultService.create_schema(
        session,
        ResultSchemaCreate(
            workspace_id=identity.workspace_id,
            name="qPCR",
            fields=[
                ResultSchemaFieldInput(name="sample_id", label="Sample", field_type="string", is_required=True),
                ResultSchemaFieldInput(name="ct", label="Ct", field_type="number", is_required=True),
            ],
        ),
        identity,
    )

    record = ResultService.create_record(
        session,
        ResultRecordCreate(
            workspace_id=identity.workspace_id,
            result_schema_id=schema.id,
            record_key="R-001",
            data={"sample_id": "S1", "ct": 23.5},
        ),
        identity,
    )

    assert record.record_key == "R-001"

    with pytest.raises(ValidationError):
        ResultService.create_record(
            session,
            ResultRecordCreate(
                workspace_id=identity.workspace_id,
                result_schema_id=schema.id,
                record_key="R-002",
                data={"sample_id": "S2", "ct": "bad"},
            ),
            identity,
        )
