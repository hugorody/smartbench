from __future__ import annotations

import pytest

from app.schemas.workflows import (
    WorkflowDefinitionCreate,
    WorkflowRunStart,
    WorkflowStateInput,
    WorkflowTransitionApply,
    WorkflowTransitionInput,
)
from app.services.exceptions import ValidationError
from app.services.workflow_service import WorkflowService


def test_workflow_transition_validation(session, identity):
    definition = WorkflowService.create_definition(
        session,
        WorkflowDefinitionCreate(
            workspace_id=identity.workspace_id,
            name="Sample Approval",
            states=[
                WorkflowStateInput(name="created", label="Created", is_initial=True),
                WorkflowStateInput(name="approved", label="Approved", is_terminal=True),
            ],
            transitions=[
                WorkflowTransitionInput(
                    name="approve",
                    from_state="created",
                    to_state="approved",
                    required_fields=["approved_by"],
                )
            ],
        ),
        identity,
    )

    run = WorkflowService.start_run(
        session,
        WorkflowRunStart(
            workspace_id=identity.workspace_id,
            workflow_definition_id=definition.id,
            run_key="WF-001",
        ),
        identity,
    )

    with pytest.raises(ValidationError):
        WorkflowService.transition_run(
            session,
            run.id,
            WorkflowTransitionApply(transition_name="approve", payload={}),
            identity,
        )

    transitioned = WorkflowService.transition_run(
        session,
        run.id,
        WorkflowTransitionApply(transition_name="approve", payload={"approved_by": "qa-user"}),
        identity,
    )
    assert transitioned.current_state == "approved"
