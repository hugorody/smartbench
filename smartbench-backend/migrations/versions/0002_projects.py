"""add projects and project resource links

Revision ID: 0002_projects
Revises: 0001_initial
Create Date: 2026-03-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "0002_projects"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("projects"):
        op.create_table(
            "projects",
            sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
            sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("updated_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("workspace_id", "name", name="uq_project_workspace_name"),
        )
        op.create_index("ix_projects_workspace_id", "projects", ["workspace_id"], unique=False)

    if not inspector.has_table("project_resource_links"):
        op.create_table(
            "project_resource_links",
            sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("resource_type", sa.String(length=64), nullable=False),
            sa.Column("resource_id", sa.String(length=64), nullable=False),
            sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
            sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("updated_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "project_id",
                "resource_type",
                "resource_id",
                name="uq_project_resource_link",
            ),
        )
        op.create_index(
            "ix_project_resource_links_workspace_id",
            "project_resource_links",
            ["workspace_id"],
            unique=False,
        )
        op.create_index(
            "ix_project_resource_links_project_id",
            "project_resource_links",
            ["project_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("project_resource_links"):
        op.drop_table("project_resource_links")
    if inspector.has_table("projects"):
        op.drop_table("projects")
