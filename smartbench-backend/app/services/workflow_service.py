"""Workflow definition and runtime state machine service."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    WorkflowDefinition,
    WorkflowRun,
    WorkflowRunEvent,
    WorkflowState,
    WorkflowTransition,
)
from app.schemas.workflows import WorkflowDefinitionCreate, WorkflowRunStart, WorkflowTransitionApply
from app.services.audit_service import AuditService
from app.services.exceptions import NotFoundError, ValidationError
from app.utils.request_context import IdentityContext


class WorkflowService:
    """Workflow CRUD and transition operations."""

    @staticmethod
    def create_definition(
        session: Session,
        payload: WorkflowDefinitionCreate,
        identity: IdentityContext,
    ) -> WorkflowDefinition:
        initial_state_count = sum(1 for state in payload.states if state.is_initial)
        if initial_state_count != 1:
            raise ValidationError("Workflow must define exactly one initial state")

        state_names = {state.name for state in payload.states}
        for transition in payload.transitions:
            if transition.from_state not in state_names or transition.to_state not in state_names:
                raise ValidationError("Workflow transition references unknown state")

        definition = WorkflowDefinition(
            workspace_id=payload.workspace_id,
            name=payload.name,
            description=payload.description,
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(definition)
        session.flush()

        for state in payload.states:
            session.add(
                WorkflowState(
                    workflow_definition_id=definition.id,
                    name=state.name,
                    label=state.label,
                    order_index=state.order_index,
                    is_initial=state.is_initial,
                    is_terminal=state.is_terminal,
                    created_by=identity.user_id,
                    updated_by=identity.user_id,
                )
            )

        for transition in payload.transitions:
            session.add(
                WorkflowTransition(
                    workflow_definition_id=definition.id,
                    name=transition.name,
                    from_state=transition.from_state,
                    to_state=transition.to_state,
                    required_fields=transition.required_fields,
                    approval_required=transition.approval_required,
                    created_by=identity.user_id,
                    updated_by=identity.user_id,
                )
            )

        AuditService.record(
            session,
            identity,
            action="workflow_definition.create",
            target_type="workflow_definition",
            target_id=definition.id,
            payload={"name": definition.name},
        )
        session.commit()
        return definition

    @staticmethod
    def start_run(session: Session, payload: WorkflowRunStart, identity: IdentityContext) -> WorkflowRun:
        definition = session.get(WorkflowDefinition, payload.workflow_definition_id)
        if definition is None:
            raise NotFoundError("Workflow definition not found")

        initial_state = session.scalar(
            select(WorkflowState)
            .where(WorkflowState.workflow_definition_id == payload.workflow_definition_id)
            .where(WorkflowState.is_initial.is_(True))
            .limit(1)
        )
        if initial_state is None:
            raise ValidationError("Workflow definition has no initial state")

        run = WorkflowRun(
            workspace_id=payload.workspace_id,
            workflow_definition_id=payload.workflow_definition_id,
            run_key=payload.run_key,
            current_state=initial_state.name,
            context_data=payload.context_data or {},
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(run)
        session.flush()

        event = WorkflowRunEvent(
            workspace_id=payload.workspace_id,
            run_id=run.id,
            transition_name="start",
            from_state="<none>",
            to_state=run.current_state,
            payload=payload.context_data,
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(event)

        AuditService.record(
            session,
            identity,
            action="workflow_run.start",
            target_type="workflow_run",
            target_id=run.id,
            payload={"run_key": run.run_key},
        )
        session.commit()
        return run

    @staticmethod
    def transition_run(
        session: Session,
        run_id: uuid.UUID,
        payload: WorkflowTransitionApply,
        identity: IdentityContext,
    ) -> WorkflowRun:
        run = session.get(WorkflowRun, run_id)
        if run is None:
            raise NotFoundError("Workflow run not found")

        transition = session.scalar(
            select(WorkflowTransition)
            .where(WorkflowTransition.workflow_definition_id == run.workflow_definition_id)
            .where(WorkflowTransition.name == payload.transition_name)
            .where(WorkflowTransition.from_state == run.current_state)
            .limit(1)
        )
        if transition is None:
            raise ValidationError("Invalid transition for current state")

        required_fields = transition.required_fields or []
        transition_payload = payload.payload or {}
        missing = [field for field in required_fields if field not in transition_payload]
        if missing:
            raise ValidationError(f"Transition missing required fields: {missing}")

        old_state = run.current_state
        run.current_state = transition.to_state
        run.updated_by = identity.user_id

        session.add(
            WorkflowRunEvent(
                workspace_id=run.workspace_id,
                run_id=run.id,
                transition_name=transition.name,
                from_state=old_state,
                to_state=transition.to_state,
                payload=transition_payload,
                created_by=identity.user_id,
                updated_by=identity.user_id,
            )
        )

        AuditService.record(
            session,
            identity,
            action="workflow_run.transition",
            target_type="workflow_run",
            target_id=run.id,
            payload={"transition": transition.name, "from": old_state, "to": run.current_state},
        )
        session.commit()
        return run

    @staticmethod
    def list_definitions(session: Session, workspace_id: uuid.UUID) -> list[WorkflowDefinition]:
        stmt = (
            select(WorkflowDefinition)
            .where(WorkflowDefinition.workspace_id == workspace_id)
            .order_by(WorkflowDefinition.name)
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def list_runs(session: Session, workspace_id: uuid.UUID) -> list[WorkflowRun]:
        stmt = (
            select(WorkflowRun)
            .where(WorkflowRun.workspace_id == workspace_id)
            .order_by(WorkflowRun.created_at.desc())
        )
        return list(session.scalars(stmt).all())
