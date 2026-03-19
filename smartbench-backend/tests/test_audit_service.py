from __future__ import annotations

from app.models import AuditEvent
from app.services.audit_service import AuditService


def test_audit_event_creation(session, identity):
    AuditService.record(
        session,
        identity,
        action="test.action",
        target_type="test_target",
        target_id="123",
        payload={"hello": "world"},
    )
    session.commit()

    event = session.query(AuditEvent).filter_by(action="test.action").one()
    assert event.target_id == "123"
    assert event.payload == {"hello": "world"}
