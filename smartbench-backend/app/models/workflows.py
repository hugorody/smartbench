"""Workflow state machine models."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import JSONType


class WorkflowDefinition(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "workflow_definitions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_workflow_definition_workspace_name"),
        Index("ix_workflow_definitions_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    states = relationship("WorkflowState", back_populates="definition", cascade="all, delete-orphan")
    transitions = relationship(
        "WorkflowTransition", back_populates="definition", cascade="all, delete-orphan"
    )


class WorkflowState(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "workflow_states"
    __table_args__ = (
        UniqueConstraint("workflow_definition_id", "name", name="uq_workflow_state_name"),
        Index("ix_workflow_states_definition_id", "workflow_definition_id"),
    )

    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_initial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    definition = relationship("WorkflowDefinition", back_populates="states")


class WorkflowTransition(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "workflow_transitions"
    __table_args__ = (
        UniqueConstraint(
            "workflow_definition_id",
            "from_state",
            "to_state",
            "name",
            name="uq_workflow_transition",
        ),
        Index("ix_workflow_transitions_definition_id", "workflow_definition_id"),
    )

    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    from_state: Mapped[str] = mapped_column(String(100), nullable=False)
    to_state: Mapped[str] = mapped_column(String(100), nullable=False)
    required_fields: Mapped[list[str] | None] = mapped_column(JSONType)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    definition = relationship("WorkflowDefinition", back_populates="transitions")


class WorkflowRun(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        Index("ix_workflow_runs_workspace_id", "workspace_id"),
        UniqueConstraint("workspace_id", "run_key", name="uq_workflow_run_key"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    run_key: Mapped[str] = mapped_column(String(64), nullable=False)
    current_state: Mapped[str] = mapped_column(String(100), nullable=False)
    context_data: Mapped[dict | None] = mapped_column(JSONType)

    events = relationship("WorkflowRunEvent", back_populates="run", cascade="all, delete-orphan")


class WorkflowRunEvent(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, db.Model):
    __tablename__ = "workflow_run_events"
    __table_args__ = (
        Index("ix_workflow_run_events_run_id", "run_id"),
        Index("ix_workflow_run_events_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False
    )
    transition_name: Mapped[str] = mapped_column(String(100), nullable=False)
    from_state: Mapped[str] = mapped_column(String(100), nullable=False)
    to_state: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONType)

    run = relationship("WorkflowRun", back_populates="events")
