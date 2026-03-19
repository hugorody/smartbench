"""Notebook template and entry services."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NotebookEntry, NotebookEntrySection, NotebookTemplate, NotebookTemplateSection
from app.schemas.notebooks import NotebookEntryCreate, NotebookSectionAppend, NotebookTemplateCreate
from app.services.audit_service import AuditService
from app.services.exceptions import NotFoundError
from app.utils.request_context import IdentityContext


class NotebookService:
    """Notebook domain operations."""

    @staticmethod
    def create_template(
        session: Session,
        payload: NotebookTemplateCreate,
        identity: IdentityContext,
    ) -> NotebookTemplate:
        template = NotebookTemplate(
            workspace_id=payload.workspace_id,
            name=payload.name,
            description=payload.description,
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(template)
        session.flush()

        for section in payload.sections:
            session.add(
                NotebookTemplateSection(
                    template_id=template.id,
                    name=section.name,
                    label=section.label,
                    order_index=section.order_index,
                    section_schema=section.section_schema,
                    created_by=identity.user_id,
                    updated_by=identity.user_id,
                )
            )

        AuditService.record(
            session,
            identity,
            action="notebook_template.create",
            target_type="notebook_template",
            target_id=template.id,
            payload={"name": template.name},
        )
        session.commit()
        return template

    @staticmethod
    def create_entry(
        session: Session,
        payload: NotebookEntryCreate,
        identity: IdentityContext,
    ) -> NotebookEntry:
        if payload.template_id is not None and session.get(NotebookTemplate, payload.template_id) is None:
            raise NotFoundError("Template not found")

        entry = NotebookEntry(
            workspace_id=payload.workspace_id,
            template_id=payload.template_id,
            title=payload.title,
            entry_key=payload.entry_key,
            status=payload.status,
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(entry)

        AuditService.record(
            session,
            identity,
            action="notebook_entry.create",
            target_type="notebook_entry",
            target_id=entry.id,
            payload={"entry_key": entry.entry_key},
        )
        session.commit()
        return entry

    @staticmethod
    def append_section(
        session: Session,
        entry_id: uuid.UUID,
        payload: NotebookSectionAppend,
        identity: IdentityContext,
    ) -> NotebookEntrySection:
        if session.get(NotebookEntry, entry_id) is None:
            raise NotFoundError("Notebook entry not found")

        section = NotebookEntrySection(
            entry_id=entry_id,
            name=payload.name,
            content_markdown=payload.content_markdown,
            structured_data=payload.structured_data,
            created_by=identity.user_id,
            updated_by=identity.user_id,
        )
        session.add(section)

        AuditService.record(
            session,
            identity,
            action="notebook_entry.append_section",
            target_type="notebook_entry",
            target_id=entry_id,
            payload=payload.model_dump(exclude_none=True),
        )
        session.commit()
        return section

    @staticmethod
    def list_templates(session: Session, workspace_id: uuid.UUID) -> list[NotebookTemplate]:
        stmt = (
            select(NotebookTemplate)
            .where(NotebookTemplate.workspace_id == workspace_id)
            .order_by(NotebookTemplate.name)
        )
        return list(session.scalars(stmt).all())

    @staticmethod
    def list_entries(session: Session, workspace_id: uuid.UUID) -> list[NotebookEntry]:
        stmt = (
            select(NotebookEntry)
            .where(NotebookEntry.workspace_id == workspace_id)
            .order_by(NotebookEntry.created_at.desc())
        )
        return list(session.scalars(stmt).all())
