from __future__ import annotations

import pytest

from app.models import AuditEvent
from app.schemas.registry import EntityCreate, EntityTypeCreate, EntityTypeFieldInput
from app.services.exceptions import ValidationError
from app.services.registry_service import RegistryService


def test_entity_schema_validation_and_creation(session, identity):
    entity_type = RegistryService.create_entity_type(
        session,
        EntityTypeCreate(
            workspace_id=identity.workspace_id,
            name="Plasmid",
            slug="plasmid",
            fields=[
                EntityTypeFieldInput(
                    name="sequence",
                    label="Sequence",
                    field_type="string",
                    is_required=True,
                ),
                EntityTypeFieldInput(name="copy_number", label="Copy Number", field_type="number"),
            ],
        ),
        identity,
    )

    entity = RegistryService.create_entity(
        session,
        EntityCreate(
            workspace_id=identity.workspace_id,
            entity_type_id=entity_type.id,
            external_id="PL-001",
            name="Demo Plasmid",
            data={"sequence": "ATGC", "copy_number": 10},
        ),
        identity,
    )

    assert entity.external_id == "PL-001"
    assert entity.data["sequence"] == "ATGC"

    events = session.query(AuditEvent).filter(AuditEvent.action == "entity.create").all()
    assert len(events) == 1



def test_entity_validation_rejects_missing_required_field(session, identity):
    entity_type = RegistryService.create_entity_type(
        session,
        EntityTypeCreate(
            workspace_id=identity.workspace_id,
            name="Strain",
            slug="strain",
            fields=[
                EntityTypeFieldInput(
                    name="organism",
                    label="Organism",
                    field_type="string",
                    is_required=True,
                )
            ],
        ),
        identity,
    )

    with pytest.raises(ValidationError):
        RegistryService.create_entity(
            session,
            EntityCreate(
                workspace_id=identity.workspace_id,
                entity_type_id=entity_type.id,
                external_id="ST-001",
                name="Incomplete Strain",
                data={},
            ),
            identity,
        )
