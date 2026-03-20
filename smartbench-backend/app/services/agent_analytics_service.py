"""Governed analytics helpers for agent queries."""

from __future__ import annotations

import statistics
import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Entity,
    NotebookEntry,
    Project,
    ProjectResourceLink,
    ResultRecord,
    ResultSchema,
    WorkflowRun,
)
from app.services.exceptions import NotFoundError


class AgentAnalyticsService:
    """Workspace/project summary and statistics used by governed agent tools."""

    RESOURCE_TYPES = ("entity", "notebook_entry", "result_record", "workflow_run")

    @staticmethod
    def workspace_overview_counts(
        session: Session,
        workspace_id: uuid.UUID,
        *,
        project_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        project: Project | None = None
        if project_id is not None:
            project = session.scalar(
                select(Project).where(Project.id == project_id).where(Project.workspace_id == workspace_id).limit(1)
            )
            if project is None:
                raise NotFoundError("Project not found in workspace")

        if project is None:
            counts = {
                "entities": int(
                    session.scalar(select(func.count(Entity.id)).where(Entity.workspace_id == workspace_id))
                    or 0
                ),
                "notebook_entries": int(
                    session.scalar(
                        select(func.count(NotebookEntry.id)).where(NotebookEntry.workspace_id == workspace_id)
                    )
                    or 0
                ),
                "result_records": int(
                    session.scalar(select(func.count(ResultRecord.id)).where(ResultRecord.workspace_id == workspace_id))
                    or 0
                ),
                "workflow_runs": int(
                    session.scalar(select(func.count(WorkflowRun.id)).where(WorkflowRun.workspace_id == workspace_id))
                    or 0
                ),
            }
        else:
            grouped = dict(
                session.execute(
                    select(ProjectResourceLink.resource_type, func.count(ProjectResourceLink.id))
                    .where(ProjectResourceLink.workspace_id == workspace_id)
                    .where(ProjectResourceLink.project_id == project.id)
                    .group_by(ProjectResourceLink.resource_type)
                ).all()
            )
            counts = {
                "entities": int(grouped.get("entity", 0)),
                "notebook_entries": int(grouped.get("notebook_entry", 0)),
                "result_records": int(grouped.get("result_record", 0)),
                "workflow_runs": int(grouped.get("workflow_run", 0)),
            }

        return {
            "scope": {
                "workspace_id": str(workspace_id),
                "project": (
                    {"id": str(project.id), "name": project.name}
                    if project is not None
                    else None
                ),
            },
            "counts": counts,
        }

    @staticmethod
    def result_numeric_stats(
        session: Session,
        workspace_id: uuid.UUID,
        *,
        schema_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        project: Project | None = None
        schema: ResultSchema | None = None
        if schema_id is not None:
            schema = session.scalar(
                select(ResultSchema)
                .where(ResultSchema.id == schema_id)
                .where(ResultSchema.workspace_id == workspace_id)
            )
            if schema is None:
                raise NotFoundError("Result schema not found in workspace")

        stmt = select(ResultRecord).where(ResultRecord.workspace_id == workspace_id)
        if schema is not None:
            stmt = stmt.where(ResultRecord.result_schema_id == schema.id)
        records = list(session.scalars(stmt).all())

        if project_id is not None:
            project = session.scalar(
                select(Project).where(Project.id == project_id).where(Project.workspace_id == workspace_id).limit(1)
            )
            if project is None:
                raise NotFoundError("Project not found in workspace")
            linked_ids = {
                parsed
                for raw_id in session.scalars(
                    select(ProjectResourceLink.resource_id)
                    .where(ProjectResourceLink.workspace_id == workspace_id)
                    .where(ProjectResourceLink.project_id == project.id)
                    .where(ProjectResourceLink.resource_type == "result_record")
                ).all()
                for parsed in [AgentAnalyticsService._safe_uuid(raw_id)]
                if parsed is not None
            }
            records = [record for record in records if record.id in linked_ids]

        numeric_fields: dict[str, list[float]] = defaultdict(list)
        for record in records:
            payload = record.data or {}
            for key, value in payload.items():
                if isinstance(value, bool):
                    continue
                if isinstance(value, int | float):
                    numeric_fields[key].append(float(value))

        field_stats: list[dict[str, Any]] = []
        for field_name, values in sorted(numeric_fields.items()):
            if not values:
                continue
            mean_value = statistics.fmean(values)
            std_dev = statistics.pstdev(values) if len(values) > 1 else 0.0
            field_stats.append(
                {
                    "field": field_name,
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "mean": mean_value,
                    "std_dev": std_dev,
                }
            )

        return {
            "scope": {
                "workspace_id": str(workspace_id),
                "project": (
                    {"id": str(project.id), "name": project.name}
                    if project is not None
                    else None
                ),
                "schema": (
                    {"id": str(schema.id), "name": schema.name}
                    if schema is not None
                    else None
                ),
            },
            "record_count": len(records),
            "fields": field_stats,
        }

    @staticmethod
    def _safe_uuid(raw_id: str) -> uuid.UUID | None:
        try:
            return uuid.UUID(raw_id)
        except ValueError:
            return None
