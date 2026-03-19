"""Three-column SmartBench application shell routes."""

from __future__ import annotations

import json
import uuid
from typing import Any

from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from app.blueprints.dashboard import bp
from app.extensions import db
from app.models import (
    AgentActionLog,
    AgentSession,
    EntityType,
    EntityTypeVersion,
    NotebookTemplate,
    Project,
    ResultSchema,
    WorkflowDefinition,
    Workspace,
)
from app.schemas.notebooks import NotebookEntryCreate
from app.schemas.projects import ProjectCreate
from app.schemas.registry import EntityCreate
from app.schemas.results import ResultRecordCreate
from app.schemas.workflows import WorkflowRunStart
from app.services.agent_session_service import AgentSessionService
from app.services.exceptions import NotFoundError, ServiceError, ValidationError
from app.services.notebook_service import NotebookService
from app.services.project_service import ProjectService
from app.services.registry_service import RegistryService
from app.services.result_service import ResultService
from app.services.workflow_service import WorkflowService
from app.utils.request_context import get_identity


def _active_workspace() -> Workspace | None:
    workspace_id = session.get("active_workspace_id")
    if workspace_id:
        try:
            workspace = db.session.get(Workspace, uuid.UUID(workspace_id))
            if workspace is not None:
                return workspace
        except ValueError:
            pass
    return db.session.query(Workspace).order_by(Workspace.created_at.asc()).first()


def _is_htmx_request() -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"


def _render_shell(
    *,
    active_section: str,
    context_template: str,
    main_template: str,
    workspace: Workspace | None,
    **context: Any,
) -> str:
    template_context = {
        "workspace": workspace,
        "active_section": active_section,
        **context,
    }
    if _is_htmx_request():
        return render_template(main_template, **template_context)

    return render_template(
        "layouts/app_shell.html",
        context_template=context_template,
        main_template=main_template,
        **template_context,
    )


def _project_from_query() -> uuid.UUID | None:
    raw_project_id = request.args.get("project_id") or request.form.get("project_id")
    if not raw_project_id:
        return None
    try:
        return uuid.UUID(raw_project_id)
    except ValueError:
        return None


def _project_context_payload(workspace: Workspace, selected_project_id: uuid.UUID | None = None) -> dict[str, Any]:
    search_query = request.args.get("q", "").strip() or None
    projects = ProjectService.list_projects(db.session, workspace.id, search=search_query)
    project_counts = ProjectService.project_link_counts(db.session, workspace.id)

    selected_project: Project | None = None
    selected_resources: dict[str, Any] = {
        "entities": [],
        "notebook_entries": [],
        "result_records": [],
        "workflow_runs": [],
        "counts": {
            "entities": 0,
            "notebook_entries": 0,
            "result_records": 0,
            "workflow_runs": 0,
        },
    }

    if selected_project_id is not None:
        try:
            selected_project = ProjectService.get_project(db.session, selected_project_id, workspace.id)
            selected_resources = ProjectService.project_resources(db.session, workspace.id, selected_project.id)
        except NotFoundError:
            selected_project = None

    return {
        "projects": projects,
        "project_counts": project_counts,
        "selected_project": selected_project,
        "selected_resources": selected_resources,
        "project_query": search_query or "",
    }


def _create_context_payload(workspace: Workspace) -> dict[str, Any]:
    return {
        "projects": ProjectService.list_projects(db.session, workspace.id),
        "entity_types": RegistryService.list_entity_types(db.session, workspace.id),
        "notebook_templates": NotebookService.list_templates(db.session, workspace.id),
        "result_schemas": ResultService.list_schemas(db.session, workspace.id),
        "workflow_definitions": WorkflowService.list_definitions(db.session, workspace.id),
    }


def _parse_json_payload(value: str, *, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if not value.strip():
        return fallback or {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValidationError("JSON payload must be an object")
    return parsed


def _parse_dynamic_field_value(field: Any, raw_value: str) -> Any:
    is_array = bool(getattr(field, "is_array", False))
    field_type = field.field_type

    if is_array:
        if not raw_value.strip():
            return []
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            parsed = [part.strip() for part in raw_value.split(",") if part.strip()]
        if not isinstance(parsed, list):
            raise ValidationError(f"Field '{field.label}' must be a JSON array or comma-separated list")
        return parsed

    if field_type in {"string", "date", "entity_ref"}:
        return raw_value
    if field_type == "number":
        if raw_value.strip() == "":
            return None
        return float(raw_value) if "." in raw_value else int(raw_value)
    if field_type == "boolean":
        return raw_value.lower() in {"true", "1", "yes", "on"}
    if field_type == "enum":
        return raw_value
    if field_type == "json":
        if raw_value.strip() == "":
            return {}
        return json.loads(raw_value)

    raise ValidationError(f"Unsupported field type '{field_type}'")


def _extract_dynamic_payload(fields: list[Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field in fields:
        raw_value = request.form.get(field.name, "")
        if raw_value.strip() == "" and not field.is_required:
            continue
        if raw_value.strip() == "" and field.is_required:
            raise ValidationError(f"Field '{field.label}' is required")
        try:
            payload[field.name] = _parse_dynamic_field_value(field, raw_value)
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValidationError(f"Invalid value for field '{field.label}': {exc}") from exc
    return payload


def _ensure_project_for_workspace(project_id: uuid.UUID | None, workspace_id: uuid.UUID) -> uuid.UUID | None:
    if project_id is None:
        return None
    ProjectService.get_project(db.session, project_id, workspace_id)
    return project_id


@bp.get("/")
@login_required
def index() -> object:
    return projects_home()


@bp.get("/app")
@login_required
def app_root() -> object:
    return redirect(url_for("dashboard.projects_home"))


@bp.get("/app/agents")
@login_required
def agents_home() -> object:
    workspace = _active_workspace()
    if workspace is None:
        return _render_shell(
            active_section="agents",
            context_template="partials/context_panels/agents.html",
            main_template="agents/main_empty.html",
            workspace=None,
            agent_sessions=[],
            active_agent_session=None,
            agent_messages=[],
        )

    agent_sessions = AgentSessionService.list_sessions(db.session, workspace.id)

    return _render_shell(
        active_section="agents",
        context_template="partials/context_panels/agents.html",
        main_template="agents/main_empty.html",
        workspace=workspace,
        agent_sessions=agent_sessions,
        active_agent_session=None,
        agent_messages=[],
    )


@bp.get("/app/agents/new")
@login_required
def new_agent_session() -> object:
    workspace = _active_workspace()
    if workspace is None:
        flash("Create a workspace before starting a conversation.", "error")
        return redirect(url_for("dashboard.agents_home"))

    identity = get_identity()
    agent_session = AgentSession(
        workspace_id=workspace.id,
        user_id=identity.user_id,
        session_label="Scientific Copilot Session",
        status="active",
        created_by=identity.user_id,
        updated_by=identity.user_id,
    )
    db.session.add(agent_session)
    db.session.commit()
    return redirect(url_for("dashboard.agent_session_detail", session_id=agent_session.id))


@bp.post("/app/agents/<uuid:session_id>/rename")
@login_required
def rename_agent_session(session_id: uuid.UUID) -> object:
    workspace = _active_workspace()
    if workspace is None:
        flash("No active workspace selected.", "error")
        return redirect(url_for("dashboard.agents_home"))

    identity = get_identity()
    new_label = request.form.get("session_label", "")

    try:
        AgentSessionService.rename_session(
            db.session,
            workspace_id=workspace.id,
            session_id=session_id,
            new_label=new_label,
            identity=identity,
        )
        flash("Conversation renamed.", "success")
    except ServiceError as exc:
        flash(str(exc), "error")

    return redirect(url_for("dashboard.agent_session_detail", session_id=session_id))


@bp.post("/app/agents/<uuid:session_id>/delete")
@login_required
def delete_agent_session(session_id: uuid.UUID) -> object:
    workspace = _active_workspace()
    if workspace is None:
        flash("No active workspace selected.", "error")
        return redirect(url_for("dashboard.agents_home"))

    identity = get_identity()

    try:
        AgentSessionService.delete_session(
            db.session,
            workspace_id=workspace.id,
            session_id=session_id,
            identity=identity,
        )
        flash("Conversation deleted.", "success")
    except ServiceError as exc:
        flash(str(exc), "error")

    return redirect(url_for("dashboard.agents_home"))


@bp.get("/app/agents/<uuid:session_id>")
@login_required
def agent_session_detail(session_id: uuid.UUID) -> object:
    workspace = _active_workspace()
    if workspace is None:
        return redirect(url_for("dashboard.agents_home"))

    agent_sessions = AgentSessionService.list_sessions(db.session, workspace.id)
    try:
        active_agent_session = AgentSessionService.get_session(
            db.session,
            workspace_id=workspace.id,
            session_id=session_id,
        )
    except NotFoundError:
        flash("Conversation not found in current workspace.", "error")
        return redirect(url_for("dashboard.agents_home"))

    action_logs = list(
        db.session.scalars(
            select(AgentActionLog)
            .where(AgentActionLog.workspace_id == workspace.id)
            .where(AgentActionLog.agent_session_id == session_id)
            .order_by(AgentActionLog.created_at.asc())
        ).all()
    )

    agent_messages: list[dict[str, Any]] = []
    for log in action_logs:
        if log.tool_name == "user_prompt":
            agent_messages.append(
                {
                    "role": "user",
                    "content": (log.tool_input or {}).get("prompt", ""),
                    "timestamp": log.created_at,
                }
            )
            continue
        if log.tool_name == "assistant_response":
            output = log.tool_output or {}
            agent_messages.append(
                {
                    "role": "assistant",
                    "content": output.get("response_text", ""),
                    "actions": output.get("actions", []),
                    "timestamp": log.created_at,
                }
            )

    return _render_shell(
        active_section="agents",
        context_template="partials/context_panels/agents.html",
        main_template="agents/main_thread.html",
        workspace=workspace,
        agent_sessions=agent_sessions,
        active_agent_session=active_agent_session,
        agent_messages=agent_messages,
    )


@bp.get("/app/projects")
@login_required
def projects_home() -> object:
    workspace = _active_workspace()
    if workspace is None:
        return _render_shell(
            active_section="projects",
            context_template="partials/context_panels/projects.html",
            main_template="projects/main_empty.html",
            workspace=None,
            projects=[],
            project_counts={},
            selected_project=None,
            selected_resources={"counts": {}},
            project_query="",
        )

    context = _project_context_payload(workspace)
    return _render_shell(
        active_section="projects",
        context_template="partials/context_panels/projects.html",
        main_template="projects/main_empty.html",
        workspace=workspace,
        **context,
    )


@bp.get("/app/projects/<uuid:project_id>")
@login_required
def project_overview(project_id: uuid.UUID) -> object:
    workspace = _active_workspace()
    if workspace is None:
        return redirect(url_for("dashboard.projects_home"))

    context = _project_context_payload(workspace, selected_project_id=project_id)
    if context["selected_project"] is None:
        flash("Project not found.", "error")
        return redirect(url_for("dashboard.projects_home"))

    return _render_shell(
        active_section="projects",
        context_template="partials/context_panels/projects.html",
        main_template="projects/main_overview.html",
        workspace=workspace,
        **context,
    )


def _find_linked_resource(resources: dict[str, Any], group: str, resource_id: uuid.UUID) -> Any | None:
    for item in resources[group]:
        if item.id == resource_id:
            return item
    return None


@bp.get("/app/projects/<uuid:project_id>/entities/<uuid:entity_id>")
@login_required
def project_entity_detail(project_id: uuid.UUID, entity_id: uuid.UUID) -> object:
    workspace = _active_workspace()
    if workspace is None:
        return redirect(url_for("dashboard.projects_home"))

    context = _project_context_payload(workspace, selected_project_id=project_id)
    entity = _find_linked_resource(context["selected_resources"], "entities", entity_id)
    if entity is None:
        flash("Entity not found in selected project.", "error")
        return redirect(url_for("dashboard.project_overview", project_id=project_id))

    return _render_shell(
        active_section="projects",
        context_template="partials/context_panels/projects.html",
        main_template="projects/main_entity_detail.html",
        workspace=workspace,
        selected_entity=entity,
        **context,
    )


@bp.get("/app/projects/<uuid:project_id>/notebooks/<uuid:notebook_id>")
@login_required
def project_notebook_detail(project_id: uuid.UUID, notebook_id: uuid.UUID) -> object:
    workspace = _active_workspace()
    if workspace is None:
        return redirect(url_for("dashboard.projects_home"))

    context = _project_context_payload(workspace, selected_project_id=project_id)
    notebook_entry = _find_linked_resource(context["selected_resources"], "notebook_entries", notebook_id)
    if notebook_entry is None:
        flash("Notebook entry not found in selected project.", "error")
        return redirect(url_for("dashboard.project_overview", project_id=project_id))

    return _render_shell(
        active_section="projects",
        context_template="partials/context_panels/projects.html",
        main_template="projects/main_notebook_detail.html",
        workspace=workspace,
        selected_notebook=notebook_entry,
        **context,
    )


@bp.get("/app/projects/<uuid:project_id>/results/<uuid:result_id>")
@login_required
def project_result_detail(project_id: uuid.UUID, result_id: uuid.UUID) -> object:
    workspace = _active_workspace()
    if workspace is None:
        return redirect(url_for("dashboard.projects_home"))

    context = _project_context_payload(workspace, selected_project_id=project_id)
    result_record = _find_linked_resource(context["selected_resources"], "result_records", result_id)
    if result_record is None:
        flash("Result record not found in selected project.", "error")
        return redirect(url_for("dashboard.project_overview", project_id=project_id))

    return _render_shell(
        active_section="projects",
        context_template="partials/context_panels/projects.html",
        main_template="projects/main_result_detail.html",
        workspace=workspace,
        selected_result=result_record,
        **context,
    )


@bp.get("/app/projects/<uuid:project_id>/workflows/<uuid:run_id>")
@login_required
def project_workflow_detail(project_id: uuid.UUID, run_id: uuid.UUID) -> object:
    workspace = _active_workspace()
    if workspace is None:
        return redirect(url_for("dashboard.projects_home"))

    context = _project_context_payload(workspace, selected_project_id=project_id)
    workflow_run = _find_linked_resource(context["selected_resources"], "workflow_runs", run_id)
    if workflow_run is None:
        flash("Workflow run not found in selected project.", "error")
        return redirect(url_for("dashboard.project_overview", project_id=project_id))

    return _render_shell(
        active_section="projects",
        context_template="partials/context_panels/projects.html",
        main_template="projects/main_workflow_detail.html",
        workspace=workspace,
        selected_workflow_run=workflow_run,
        **context,
    )


@bp.get("/app/create")
@login_required
def create_home() -> object:
    workspace = _active_workspace()
    selected_project_id = _project_from_query()
    if workspace is None:
        return _render_shell(
            active_section="create",
            context_template="partials/context_panels/create.html",
            main_template="create/main_empty.html",
            workspace=None,
            projects=[],
            entity_types=[],
            notebook_templates=[],
            result_schemas=[],
            workflow_definitions=[],
            selected_project_id=selected_project_id,
        )

    context = _create_context_payload(workspace)
    return _render_shell(
        active_section="create",
        context_template="partials/context_panels/create.html",
        main_template="create/main_empty.html",
        workspace=workspace,
        selected_project_id=selected_project_id,
        **context,
    )


@bp.route("/app/create/project/new", methods=["GET", "POST"])
@login_required
def create_project() -> object:
    workspace = _active_workspace()
    if workspace is None:
        flash("No workspace available.", "error")
        return redirect(url_for("dashboard.create_home"))

    context = _create_context_payload(workspace)

    if request.method == "POST":
        identity = get_identity()
        try:
            project = ProjectService.create_project(
                db.session,
                ProjectCreate(
                    workspace_id=workspace.id,
                    name=request.form.get("name", "").strip(),
                    description=request.form.get("description", "").strip() or None,
                ),
                identity,
            )
            flash("Project created.", "success")
            return redirect(url_for("dashboard.project_overview", project_id=project.id))
        except ServiceError as exc:
            flash(str(exc), "error")

    return _render_shell(
        active_section="create",
        context_template="partials/context_panels/create.html",
        main_template="create/project_form.html",
        workspace=workspace,
        **context,
    )


@bp.route("/app/create/entity-types/<uuid:entity_type_id>/new", methods=["GET", "POST"])
@login_required
def create_entity_from_type(entity_type_id: uuid.UUID) -> object:
    workspace = _active_workspace()
    if workspace is None:
        flash("No workspace available.", "error")
        return redirect(url_for("dashboard.create_home"))

    context = _create_context_payload(workspace)
    selected_project_id = _project_from_query()

    entity_type = db.session.scalar(
        select(EntityType)
        .where(EntityType.workspace_id == workspace.id)
        .where(EntityType.id == entity_type_id)
        .limit(1)
    )
    if entity_type is None:
        flash("Entity type not found.", "error")
        return redirect(url_for("dashboard.create_home"))

    active_version: EntityTypeVersion | None = db.session.get(EntityTypeVersion, entity_type.active_version_id)
    fields = list(active_version.fields) if active_version is not None else []

    if request.method == "POST":
        identity = get_identity()
        try:
            selected_project_id = _ensure_project_for_workspace(selected_project_id, workspace.id)
            payload = _extract_dynamic_payload(fields)
            entity = RegistryService.create_entity(
                db.session,
                EntityCreate(
                    workspace_id=workspace.id,
                    entity_type_id=entity_type.id,
                    external_id=request.form.get("external_id", "").strip(),
                    name=request.form.get("name", "").strip(),
                    data=payload,
                ),
                identity,
            )
            if selected_project_id is not None:
                ProjectService.link_resource(
                    db.session,
                    workspace_id=workspace.id,
                    project_id=selected_project_id,
                    resource_type="entity",
                    resource_id=entity.id,
                    identity=identity,
                )
                return redirect(
                    url_for(
                        "dashboard.project_entity_detail",
                        project_id=selected_project_id,
                        entity_id=entity.id,
                    )
                )
            flash("Entity created.", "success")
            return redirect(url_for("dashboard.projects_home"))
        except ServiceError as exc:
            flash(str(exc), "error")

    return _render_shell(
        active_section="create",
        context_template="partials/context_panels/create.html",
        main_template="create/entity_form.html",
        workspace=workspace,
        entity_type=entity_type,
        entity_fields=fields,
        selected_project_id=selected_project_id,
        **context,
    )


@bp.route("/app/create/notebook-templates/<uuid:template_id>/new", methods=["GET", "POST"])
@login_required
def create_notebook_from_template(template_id: uuid.UUID) -> object:
    workspace = _active_workspace()
    if workspace is None:
        flash("No workspace available.", "error")
        return redirect(url_for("dashboard.create_home"))

    context = _create_context_payload(workspace)
    selected_project_id = _project_from_query()

    template = db.session.scalar(
        select(NotebookTemplate)
        .where(NotebookTemplate.workspace_id == workspace.id)
        .where(NotebookTemplate.id == template_id)
        .limit(1)
    )
    if template is None:
        flash("Notebook template not found.", "error")
        return redirect(url_for("dashboard.create_home"))

    if request.method == "POST":
        identity = get_identity()
        try:
            selected_project_id = _ensure_project_for_workspace(selected_project_id, workspace.id)
            entry = NotebookService.create_entry(
                db.session,
                NotebookEntryCreate(
                    workspace_id=workspace.id,
                    template_id=template.id,
                    title=request.form.get("title", "").strip(),
                    entry_key=request.form.get("entry_key", "").strip(),
                    status=request.form.get("status", "draft").strip() or "draft",
                ),
                identity,
            )
            if selected_project_id is not None:
                ProjectService.link_resource(
                    db.session,
                    workspace_id=workspace.id,
                    project_id=selected_project_id,
                    resource_type="notebook_entry",
                    resource_id=entry.id,
                    identity=identity,
                )
                return redirect(
                    url_for(
                        "dashboard.project_notebook_detail",
                        project_id=selected_project_id,
                        notebook_id=entry.id,
                    )
                )
            flash("Notebook entry created.", "success")
            return redirect(url_for("dashboard.projects_home"))
        except ServiceError as exc:
            flash(str(exc), "error")

    return _render_shell(
        active_section="create",
        context_template="partials/context_panels/create.html",
        main_template="create/notebook_form.html",
        workspace=workspace,
        notebook_template=template,
        selected_project_id=selected_project_id,
        **context,
    )


@bp.route("/app/create/result-schemas/<uuid:schema_id>/new", methods=["GET", "POST"])
@login_required
def create_result_from_schema(schema_id: uuid.UUID) -> object:
    workspace = _active_workspace()
    if workspace is None:
        flash("No workspace available.", "error")
        return redirect(url_for("dashboard.create_home"))

    context = _create_context_payload(workspace)
    selected_project_id = _project_from_query()

    result_schema = db.session.scalar(
        select(ResultSchema)
        .where(ResultSchema.workspace_id == workspace.id)
        .where(ResultSchema.id == schema_id)
        .limit(1)
    )
    if result_schema is None:
        flash("Result schema not found.", "error")
        return redirect(url_for("dashboard.create_home"))

    if request.method == "POST":
        identity = get_identity()
        try:
            selected_project_id = _ensure_project_for_workspace(selected_project_id, workspace.id)
            payload = _extract_dynamic_payload(list(result_schema.fields))
            record = ResultService.create_record(
                db.session,
                ResultRecordCreate(
                    workspace_id=workspace.id,
                    result_schema_id=result_schema.id,
                    record_key=request.form.get("record_key", "").strip(),
                    data=payload,
                ),
                identity,
            )
            if selected_project_id is not None:
                ProjectService.link_resource(
                    db.session,
                    workspace_id=workspace.id,
                    project_id=selected_project_id,
                    resource_type="result_record",
                    resource_id=record.id,
                    identity=identity,
                )
                return redirect(
                    url_for(
                        "dashboard.project_result_detail",
                        project_id=selected_project_id,
                        result_id=record.id,
                    )
                )
            flash("Result record created.", "success")
            return redirect(url_for("dashboard.projects_home"))
        except ServiceError as exc:
            flash(str(exc), "error")

    return _render_shell(
        active_section="create",
        context_template="partials/context_panels/create.html",
        main_template="create/result_form.html",
        workspace=workspace,
        result_schema=result_schema,
        result_fields=list(result_schema.fields),
        selected_project_id=selected_project_id,
        **context,
    )


@bp.route("/app/create/workflow-definitions/<uuid:workflow_id>/new", methods=["GET", "POST"])
@login_required
def create_workflow_run(workflow_id: uuid.UUID) -> object:
    workspace = _active_workspace()
    if workspace is None:
        flash("No workspace available.", "error")
        return redirect(url_for("dashboard.create_home"))

    context = _create_context_payload(workspace)
    selected_project_id = _project_from_query()

    workflow_definition = db.session.scalar(
        select(WorkflowDefinition)
        .where(WorkflowDefinition.workspace_id == workspace.id)
        .where(WorkflowDefinition.id == workflow_id)
        .limit(1)
    )
    if workflow_definition is None:
        flash("Workflow definition not found.", "error")
        return redirect(url_for("dashboard.create_home"))

    if request.method == "POST":
        identity = get_identity()
        try:
            selected_project_id = _ensure_project_for_workspace(selected_project_id, workspace.id)
            run = WorkflowService.start_run(
                db.session,
                WorkflowRunStart(
                    workspace_id=workspace.id,
                    workflow_definition_id=workflow_definition.id,
                    run_key=request.form.get("run_key", "").strip(),
                    context_data=_parse_json_payload(request.form.get("context_json", "{}")),
                ),
                identity,
            )
            if selected_project_id is not None:
                ProjectService.link_resource(
                    db.session,
                    workspace_id=workspace.id,
                    project_id=selected_project_id,
                    resource_type="workflow_run",
                    resource_id=run.id,
                    identity=identity,
                )
                return redirect(
                    url_for(
                        "dashboard.project_workflow_detail",
                        project_id=selected_project_id,
                        run_id=run.id,
                    )
                )
            flash("Workflow run started.", "success")
            return redirect(url_for("dashboard.projects_home"))
        except (ServiceError, json.JSONDecodeError) as exc:
            flash(str(exc), "error")

    return _render_shell(
        active_section="create",
        context_template="partials/context_panels/create.html",
        main_template="create/workflow_form.html",
        workspace=workspace,
        workflow_definition=workflow_definition,
        selected_project_id=selected_project_id,
        **context,
    )


@bp.context_processor
def inject_navigation_context() -> dict[str, Any]:
    return {
        "all_workspaces": db.session.query(Workspace).order_by(Workspace.name).all(),
        "active_workspace_id": session.get("active_workspace_id"),
        "current_user": current_user,
    }
