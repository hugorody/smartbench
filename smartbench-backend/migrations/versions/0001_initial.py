"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-19
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None



def upgrade() -> None:
    bind = op.get_bind()
    from app.models import (  # local import keeps migration tied to project metadata
        AgentActionLog,
        AgentSession,
        AuditEvent,
        Entity,
        EntityRelationship,
        EntityType,
        EntityTypeField,
        EntityTypeVersion,
        FileAsset,
        FileLink,
        Membership,
        NotebookEntry,
        NotebookEntrySection,
        NotebookLink,
        NotebookTemplate,
        NotebookTemplateSection,
        Permission,
        ResultRecord,
        ResultSchema,
        ResultSchemaField,
        Role,
        RolePermission,
        User,
        WorkflowDefinition,
        WorkflowRun,
        WorkflowRunEvent,
        WorkflowState,
        WorkflowTransition,
        Workspace,
    )

    _ = (
        AgentActionLog,
        AgentSession,
        AuditEvent,
        Entity,
        EntityRelationship,
        EntityType,
        EntityTypeField,
        EntityTypeVersion,
        FileAsset,
        FileLink,
        Membership,
        NotebookEntry,
        NotebookEntrySection,
        NotebookLink,
        NotebookTemplate,
        NotebookTemplateSection,
        Permission,
        ResultRecord,
        ResultSchema,
        ResultSchemaField,
        Role,
        RolePermission,
        User,
        WorkflowDefinition,
        WorkflowRun,
        WorkflowRunEvent,
        WorkflowState,
        WorkflowTransition,
        Workspace,
    )

    Workspace.metadata.create_all(bind=bind)



def downgrade() -> None:
    bind = op.get_bind()
    from app.models import Workspace

    Workspace.metadata.drop_all(bind=bind)
