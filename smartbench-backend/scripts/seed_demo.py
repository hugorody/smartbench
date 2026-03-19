"""Seed demo SmartBench workspace and baseline records."""

from __future__ import annotations

import sys

from flask import Flask
from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from app.models import (
    Entity,
    EntityType,
    Membership,
    NotebookEntry,
    NotebookTemplate,
    Permission,
    Project,
    ResultRecord,
    ResultSchema,
    Role,
    RolePermission,
    User,
    WorkflowDefinition,
    WorkflowRun,
    Workspace,
)
from app.schemas.notebooks import NotebookEntryCreate, NotebookTemplateCreate, NotebookTemplateSectionInput
from app.schemas.projects import ProjectCreate
from app.schemas.registry import EntityCreate, EntityTypeCreate, EntityTypeFieldInput
from app.schemas.results import ResultRecordCreate, ResultSchemaCreate, ResultSchemaFieldInput
from app.schemas.workflows import (
    WorkflowDefinitionCreate,
    WorkflowRunStart,
    WorkflowStateInput,
    WorkflowTransitionInput,
)
from app.security.rbac import PermissionCodes
from app.services.notebook_service import NotebookService
from app.services.project_service import ProjectService
from app.services.registry_service import RegistryService
from app.services.result_service import ResultService
from app.services.workflow_service import WorkflowService
from app.utils.request_context import IdentityContext


def ensure_schema_ready() -> None:
    """Ensure migrations have been applied before seeding."""
    inspector = inspect(db.engine)
    required_tables = [
        "workspaces",
        "users",
        "roles",
        "permissions",
        "memberships",
        "projects",
        "entity_types",
        "result_schemas",
        "workflow_definitions",
    ]
    missing = [table for table in required_tables if not inspector.has_table(table)]
    if missing:
        missing_csv = ", ".join(missing)
        raise RuntimeError(
            "Database schema is not initialized. "
            f"Missing tables: {missing_csv}. "
            "Run migrations first: ./scripts/db_upgrade.sh or make migrate"
        )


def seed_permissions() -> dict[str, Permission]:
    permissions = {
        PermissionCodes.ENTITY_TYPE_WRITE: "Manage dynamic entity schemas",
        PermissionCodes.ENTITY_WRITE: "Create and update entities",
        PermissionCodes.NOTEBOOK_WRITE: "Create and update notebook records",
        PermissionCodes.RESULT_WRITE: "Manage result schemas and records",
        PermissionCodes.WORKFLOW_WRITE: "Manage workflows and transitions",
        PermissionCodes.AUDIT_READ: "Read audit trail",
        PermissionCodes.AGENT_USE: "Use Scientific Copilot",
    }
    created: dict[str, Permission] = {}
    for code, description in permissions.items():
        existing = db.session.query(Permission).filter_by(code=code).first()
        if existing:
            created[code] = existing
            continue
        permission = Permission(code=code, description=description)
        db.session.add(permission)
        created[code] = permission
    db.session.flush()
    return created


def assign_all_permissions(role: Role, permissions: dict[str, Permission]) -> None:
    for permission in permissions.values():
        exists = (
            db.session.query(RolePermission)
            .filter_by(role_id=role.id, permission_id=permission.id)
            .first()
        )
        if exists:
            continue
        db.session.add(RolePermission(role_id=role.id, permission_id=permission.id))


def seed_demo_data(app: Flask) -> None:
    with app.app_context():
        ensure_schema_ready()

        workspace = db.session.query(Workspace).filter_by(slug="demo-workspace").first()
        if workspace is None:
            workspace = Workspace(name="SmartBench Demo Workspace", slug="demo-workspace")
            db.session.add(workspace)
            db.session.flush()

        admin_user = db.session.query(User).filter_by(email="admin@smartbench.local").first()
        if admin_user is None:
            admin_user = User(email="admin@smartbench.local", full_name="SmartBench Admin")
            db.session.add(admin_user)
            db.session.flush()

        admin_role = (
            db.session.query(Role)
            .filter_by(workspace_id=workspace.id, name="workspace_admin")
            .first()
        )
        if admin_role is None:
            admin_role = Role(
                workspace_id=workspace.id,
                name="workspace_admin",
                description="Full admin",
            )
            db.session.add(admin_role)
            db.session.flush()

        if (
            db.session.query(Membership)
            .filter_by(workspace_id=workspace.id, user_id=admin_user.id)
            .first()
            is None
        ):
            db.session.add(
                Membership(workspace_id=workspace.id, user_id=admin_user.id, role_id=admin_role.id)
            )

        permissions = seed_permissions()
        assign_all_permissions(admin_role, permissions)

        identity = IdentityContext(user_id=admin_user.id, workspace_id=workspace.id, source="seed")

        existing_entity_type_names = {
            item.name
            for item in db.session.query(EntityType).filter_by(workspace_id=workspace.id).all()
        }

        for entity_type_name, slug, fields in [
            (
                "Plasmid",
                "plasmid",
                [
                    EntityTypeFieldInput(name="sequence", label="Sequence", field_type="string", is_required=True),
                    EntityTypeFieldInput(name="backbone", label="Backbone", field_type="string"),
                ],
            ),
            (
                "Strain",
                "strain",
                [
                    EntityTypeFieldInput(name="organism", label="Organism", field_type="string", is_required=True),
                    EntityTypeFieldInput(name="genotype", label="Genotype", field_type="string"),
                ],
            ),
            (
                "ProteinBatch",
                "protein-batch",
                [
                    EntityTypeFieldInput(
                        name="protein_name",
                        label="Protein Name",
                        field_type="string",
                        is_required=True,
                    ),
                    EntityTypeFieldInput(
                        name="concentration_mg_ml",
                        label="Concentration",
                        field_type="number",
                    ),
                ],
            ),
        ]:
            if entity_type_name not in existing_entity_type_names:
                RegistryService.create_entity_type(
                    db.session,
                    EntityTypeCreate(
                        workspace_id=workspace.id,
                        name=entity_type_name,
                        slug=slug,
                        description=f"Demo schema for {entity_type_name}",
                        fields=fields,
                    ),
                    identity,
                )

        project = db.session.query(Project).filter_by(workspace_id=workspace.id, name="Demo Project").first()
        if project is None:
            project = ProjectService.create_project(
                db.session,
                ProjectCreate(
                    workspace_id=workspace.id,
                    name="Demo Project",
                    description="Seeded project for SmartBench app-shell explorer",
                ),
                identity,
            )

        if not db.session.query(NotebookTemplate).filter_by(workspace_id=workspace.id).first():
            NotebookService.create_template(
                db.session,
                NotebookTemplateCreate(
                    workspace_id=workspace.id,
                    name="Standard Experiment Log",
                    description="Template for routine experiment execution",
                    sections=[
                        NotebookTemplateSectionInput(
                            name="objective",
                            label="Objective",
                            order_index=1,
                            section_schema={"type": "markdown"},
                        ),
                        NotebookTemplateSectionInput(
                            name="methods",
                            label="Methods",
                            order_index=2,
                            section_schema={"type": "markdown"},
                        ),
                    ],
                ),
                identity,
            )

        if not db.session.query(ResultSchema).filter_by(workspace_id=workspace.id).first():
            ResultService.create_schema(
                db.session,
                ResultSchemaCreate(
                    workspace_id=workspace.id,
                    name="qPCR Result Table",
                    description="Demo qPCR output schema",
                    fields=[
                        ResultSchemaFieldInput(
                            name="sample_id",
                            label="Sample ID",
                            field_type="string",
                            is_required=True,
                        ),
                        ResultSchemaFieldInput(
                            name="ct_value",
                            label="Ct",
                            field_type="number",
                            is_required=True,
                        ),
                    ],
                ),
                identity,
            )

        if not db.session.query(WorkflowDefinition).filter_by(workspace_id=workspace.id).first():
            WorkflowService.create_definition(
                db.session,
                WorkflowDefinitionCreate(
                    workspace_id=workspace.id,
                    name="Sample Intake Workflow",
                    description="Demo workflow for sample intake and release",
                    states=[
                        WorkflowStateInput(name="created", label="Created", is_initial=True),
                        WorkflowStateInput(name="in_review", label="In Review"),
                        WorkflowStateInput(name="approved", label="Approved", is_terminal=True),
                    ],
                    transitions=[
                        WorkflowTransitionInput(name="submit", from_state="created", to_state="in_review"),
                        WorkflowTransitionInput(name="approve", from_state="in_review", to_state="approved"),
                    ],
                ),
                identity,
            )

        plasmid_type = (
            db.session.query(EntityType)
            .filter_by(workspace_id=workspace.id, name="Plasmid")
            .first()
        )
        if plasmid_type is not None:
            plasmid_entity = (
                db.session.query(Entity)
                .filter_by(workspace_id=workspace.id, external_id="PLASMID-001")
                .first()
            )
            if plasmid_entity is None:
                plasmid_entity = RegistryService.create_entity(
                    db.session,
                    EntityCreate(
                        workspace_id=workspace.id,
                        entity_type_id=plasmid_type.id,
                        external_id="PLASMID-001",
                        name="pSB-Demo-Backbone",
                        data={"sequence": "ATGCGT", "backbone": "pUC19"},
                    ),
                    identity,
                )
            ProjectService.link_resource(
                db.session,
                workspace_id=workspace.id,
                project_id=project.id,
                resource_type="entity",
                resource_id=plasmid_entity.id,
                identity=identity,
            )

        notebook_template = db.session.query(NotebookTemplate).filter_by(workspace_id=workspace.id).first()
        if notebook_template is not None:
            notebook_entry = (
                db.session.query(NotebookEntry)
                .filter_by(workspace_id=workspace.id, entry_key="NB-0001")
                .first()
            )
            if notebook_entry is None:
                notebook_entry = NotebookService.create_entry(
                    db.session,
                    NotebookEntryCreate(
                        workspace_id=workspace.id,
                        template_id=notebook_template.id,
                        title="Seeded Demo Notebook Entry",
                        entry_key="NB-0001",
                    ),
                    identity,
                )
            ProjectService.link_resource(
                db.session,
                workspace_id=workspace.id,
                project_id=project.id,
                resource_type="notebook_entry",
                resource_id=notebook_entry.id,
                identity=identity,
            )

        result_schema = db.session.query(ResultSchema).filter_by(workspace_id=workspace.id).first()
        if result_schema is not None:
            result_record = (
                db.session.query(ResultRecord)
                .filter_by(workspace_id=workspace.id, record_key="QPCR-0001")
                .first()
            )
            if result_record is None:
                result_record = ResultService.create_record(
                    db.session,
                    ResultRecordCreate(
                        workspace_id=workspace.id,
                        result_schema_id=result_schema.id,
                        record_key="QPCR-0001",
                        data={"sample_id": "Sample-001", "ct_value": 18.2},
                    ),
                    identity,
                )
            ProjectService.link_resource(
                db.session,
                workspace_id=workspace.id,
                project_id=project.id,
                resource_type="result_record",
                resource_id=result_record.id,
                identity=identity,
            )

        workflow_definition = db.session.query(WorkflowDefinition).filter_by(workspace_id=workspace.id).first()
        if workflow_definition is not None:
            workflow_run = (
                db.session.query(WorkflowRun)
                .filter_by(workspace_id=workspace.id, run_key="RUN-0001")
                .first()
            )
            if workflow_run is None:
                workflow_run = WorkflowService.start_run(
                    db.session,
                    WorkflowRunStart(
                        workspace_id=workspace.id,
                        workflow_definition_id=workflow_definition.id,
                        run_key="RUN-0001",
                        context_data={"sample_id": "Sample-001"},
                    ),
                    identity,
                )
            ProjectService.link_resource(
                db.session,
                workspace_id=workspace.id,
                project_id=project.id,
                resource_type="workflow_run",
                resource_id=workflow_run.id,
                identity=identity,
            )

        db.session.commit()
        print("seed complete (idempotent)")


if __name__ == "__main__":
    try:
        seed_demo_data(create_app())
    except RuntimeError as exc:
        print(f"[seed_demo] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
