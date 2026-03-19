"""Project organization and project-resource linking services."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Entity,
    NotebookEntry,
    Project,
    ProjectResourceLink,
    ResultRecord,
    WorkflowRun,
)
from app.schemas.projects import ProjectCreate
from app.services.audit_service import AuditService
from app.services.exceptions import NotFoundError, ValidationError
from app.utils.request_context import IdentityContext


class ProjectService:
    """Workspace-scoped project lifecycle and linking operations."""

    VALID_RESOURCE_TYPES = frozenset({"entity", "notebook_entry", "result_record", "workflow_run"})

    @staticmethod
    def create_project(session: Session, payload: ProjectCreate, identity: IdentityContext) -> Project:
        existing = session.scalar(
            select(Project)
            .where(Project.workspace_id == payload.workspace_id)
            .where(Project.name == payload.name)
            .limit(1)
        )
        if existing is not None:
            raise ValidationError(f"Project '{payload.name}' already exists in this workspace")

        project = Project(
            workspace_id=payload.workspace_id,
            name=payload.name,
            description=payload.description,
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(project)

        AuditService.record(
            session,
            identity,
            action="project.create",
            target_type="project",
            target_id=project.id,
            payload={"name": project.name},
        )
        session.commit()
        return project

    @staticmethod
    def list_projects(session: Session, workspace_id: uuid.UUID, search: str | None = None) -> list[Project]:
        stmt = select(Project).where(Project.workspace_id == workspace_id).where(Project.is_archived.is_(False))
        if search:
            stmt = stmt.where(Project.name.ilike(f"%{search}%"))
        stmt = stmt.order_by(Project.name)
        return list(session.scalars(stmt).all())

    @staticmethod
    def get_project(session: Session, project_id: uuid.UUID, workspace_id: uuid.UUID | None = None) -> Project:
        stmt = select(Project).where(Project.id == project_id)
        if workspace_id is not None:
            stmt = stmt.where(Project.workspace_id == workspace_id)
        project = session.scalar(stmt.limit(1))
        if project is None:
            raise NotFoundError("Project not found")
        return project

    @staticmethod
    def link_resource(
        session: Session,
        *,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID | str,
        identity: IdentityContext,
    ) -> ProjectResourceLink:
        if resource_type not in ProjectService.VALID_RESOURCE_TYPES:
            valid_types = ", ".join(sorted(ProjectService.VALID_RESOURCE_TYPES))
            raise ValidationError(f"resource_type must be one of: {valid_types}")

        project = ProjectService.get_project(session, project_id=project_id, workspace_id=workspace_id)
        resource_id_str = str(resource_id)

        existing = session.scalar(
            select(ProjectResourceLink)
            .where(ProjectResourceLink.project_id == project.id)
            .where(ProjectResourceLink.resource_type == resource_type)
            .where(ProjectResourceLink.resource_id == resource_id_str)
            .limit(1)
        )
        if existing is not None:
            return existing

        link = ProjectResourceLink(
            workspace_id=workspace_id,
            project_id=project.id,
            resource_type=resource_type,
            resource_id=resource_id_str,
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(link)

        AuditService.record(
            session,
            identity,
            action="project.link_resource",
            target_type="project",
            target_id=project.id,
            payload={"resource_type": resource_type, "resource_id": resource_id_str},
        )
        session.commit()
        return link

    @staticmethod
    def project_link_counts(session: Session, workspace_id: uuid.UUID) -> dict[uuid.UUID, int]:
        stmt = (
            select(ProjectResourceLink.project_id, func.count(ProjectResourceLink.id))
            .where(ProjectResourceLink.workspace_id == workspace_id)
            .group_by(ProjectResourceLink.project_id)
        )
        rows = session.execute(stmt).all()
        return {project_id: int(count) for project_id, count in rows}

    @staticmethod
    def _parse_uuid_ids(values: list[str]) -> list[uuid.UUID]:
        parsed: list[uuid.UUID] = []
        for value in values:
            try:
                parsed.append(uuid.UUID(value))
            except ValueError:
                continue
        return parsed

    @staticmethod
    def project_resources(
        session: Session,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> dict[str, Any]:
        links = list(
            session.scalars(
                select(ProjectResourceLink)
                .where(ProjectResourceLink.workspace_id == workspace_id)
                .where(ProjectResourceLink.project_id == project_id)
                .order_by(ProjectResourceLink.created_at.desc())
            ).all()
        )

        link_ids: dict[str, list[str]] = {resource_type: [] for resource_type in ProjectService.VALID_RESOURCE_TYPES}
        for link in links:
            link_ids.setdefault(link.resource_type, []).append(link.resource_id)

        entities = ProjectService._load_entities(session, workspace_id, link_ids.get("entity", []))
        notebook_entries = ProjectService._load_notebook_entries(
            session, workspace_id, link_ids.get("notebook_entry", [])
        )
        result_records = ProjectService._load_result_records(
            session, workspace_id, link_ids.get("result_record", [])
        )
        workflow_runs = ProjectService._load_workflow_runs(session, workspace_id, link_ids.get("workflow_run", []))

        return {
            "entities": entities,
            "notebook_entries": notebook_entries,
            "result_records": result_records,
            "workflow_runs": workflow_runs,
            "counts": {
                "entities": len(entities),
                "notebook_entries": len(notebook_entries),
                "result_records": len(result_records),
                "workflow_runs": len(workflow_runs),
            },
        }

    @staticmethod
    def _load_entities(session: Session, workspace_id: uuid.UUID, ids: list[str]) -> list[Entity]:
        uuid_ids = ProjectService._parse_uuid_ids(ids)
        if not uuid_ids:
            return []
        stmt = (
            select(Entity)
            .where(Entity.workspace_id == workspace_id)
            .where(Entity.id.in_(uuid_ids))
            .order_by(Entity.created_at.desc())
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def _load_notebook_entries(session: Session, workspace_id: uuid.UUID, ids: list[str]) -> list[NotebookEntry]:
        uuid_ids = ProjectService._parse_uuid_ids(ids)
        if not uuid_ids:
            return []
        stmt = (
            select(NotebookEntry)
            .where(NotebookEntry.workspace_id == workspace_id)
            .where(NotebookEntry.id.in_(uuid_ids))
            .order_by(NotebookEntry.created_at.desc())
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def _load_result_records(session: Session, workspace_id: uuid.UUID, ids: list[str]) -> list[ResultRecord]:
        uuid_ids = ProjectService._parse_uuid_ids(ids)
        if not uuid_ids:
            return []
        stmt = (
            select(ResultRecord)
            .where(ResultRecord.workspace_id == workspace_id)
            .where(ResultRecord.id.in_(uuid_ids))
            .order_by(ResultRecord.created_at.desc())
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def _load_workflow_runs(session: Session, workspace_id: uuid.UUID, ids: list[str]) -> list[WorkflowRun]:
        uuid_ids = ProjectService._parse_uuid_ids(ids)
        if not uuid_ids:
            return []
        stmt = (
            select(WorkflowRun)
            .where(WorkflowRun.workspace_id == workspace_id)
            .where(WorkflowRun.id.in_(uuid_ids))
            .order_by(WorkflowRun.created_at.desc())
        )
        return list(session.scalars(stmt).all())
