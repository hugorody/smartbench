# SmartBench Backend

MIT-licensed backend-first bootstrap for **SmartBench**, a Benchling-like scientific data platform with native OpenAI agent integration.

## Highlights

- Flask 3 + SQLAlchemy 2 + Flask-Migrate
- PostgreSQL-first schema with UUID keys and JSONB-compatible dynamic payloads
- Dynamic entity type/version engine
- Notebook templates and entries
- Result schemas and records
- Configurable workflow state machines
- Agent-safe service and tool orchestration scaffold (OpenAI Responses API wrapper)
- Immutable audit trail for every mutation path in service layer
- Jinja dashboard scaffold with HTMX/Tailwind for internal operations
- Docker Compose local stack (`web`, `postgres`, `redis`, optional `pgadmin`)
- Pytest coverage for key validation and workflow invariants

## Workbench UI Shell

The server-rendered UI now uses a persistent three-column SmartBench shell:

1. Left fixed sidebar (dark navy) with only three primary buttons: `Agents`, `Projects`, `Create`
2. Context panel for section-specific browsing (agent threads, project explorer, create launcher)
3. Main canvas for details/forms (conversation, project resources, schema-driven create flows)

Route entry points:

- `/` -> redirects authenticated users to `/app/projects`
- `/app/agents` and `/app/agents/<session_id>`
- `/app/projects` and `/app/projects/<project_id>`
- `/app/create` and schema-driven create routes under `/app/create/*`

Projects are now first-class backend resources (`projects`, `project_resource_links`) and seeded with demo links so the explorer has real content.

### Modern UX Layer

The shell includes modern interaction patterns while remaining Flask + Jinja + HTMX:

- HTMX request progress bar at the top of the viewport
- Quick Actions command palette (`Ctrl/Cmd+K`)
- Context panel toggle shortcut (`Ctrl/Cmd+B`) plus explicit hide/show controls
- Subtle ambient background, panel motion, and improved focus states

## Quick Start

1. Copy env file:

```bash
cp .env.example .env
```

2. Start local stack:

```bash
docker compose up --build
```

3. Open app:

- App: `http://localhost:8000`
- pgAdmin: `http://localhost:5050`

## Homologation

Run the full deterministic local homologation pipeline (docker build/up, environment verification, migrations, seed, pytest, smoke API checks):

```bash
cp .env.example .env
make homologate
```

Individual operational targets:

```bash
make up
make migrate
make seed
make test
make smoke
make down
make reset
```

## Local Dev Without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
flask --app app:create_app db upgrade
python -m scripts.seed_demo
flask --app app:create_app --debug run --host 0.0.0.0 --port 8000
```

## Database Migrations

Initial migration is included in `migrations/versions/0001_initial.py`.

Run upgrade:

```bash
flask --app app:create_app db upgrade
```

Create a new migration:

```bash
flask --app app:create_app db migrate -m "describe change"
```

## Seed Data

Run demo seed:

```bash
python -m scripts.seed_demo
```

The seed is idempotent and requires migrated schema. If migrations were not applied, it fails with an actionable error.

Seed creates:

- Workspace: `SmartBench Demo Workspace`
- User: `admin@smartbench.local`
- Role: `workspace_admin`
- Entity Types: `Plasmid`, `Strain`, `ProteinBatch`
- Notebook Template: `Standard Experiment Log`
- Result Schema: `qPCR Result Table`
- Workflow: `Sample Intake Workflow`

## Tests

```bash
pytest
```

## Architecture Summary

- `app/models/`: relational + dynamic JSONB-capable schema
- `app/schemas/`: Pydantic v2 request/validation models
- `app/services/`: domain logic, validation, transitions, audit writes
- `app/blueprints/`: thin HTTP routes (API + dashboard views)
- `app/services/agent_service.py`: governed copilot orchestration
- `app/tools/tool_registry.py`: internal agent tool catalog + dispatch
- `app/services/introspection_service.py`: machine-readable schema context
- `app/semantic/serializer.py`: retrieval-oriented semantic summaries

## Key API Surface

- `GET /api/health`
- `POST /api/workspaces`
- `GET|POST /api/registry/entity-types`
- `GET|POST /api/registry/entities`
- `GET|POST /api/notebooks/templates`
- `GET|POST /api/notebooks/entries`
- `GET|POST /api/results/schemas`
- `GET|POST /api/results/records`
- `GET|POST /api/workflows/definitions`
- `GET|POST /api/workflows/runs`
- `POST /api/workflows/runs/<id>/transition`
- `GET /api/audit/events`
- `GET /api/audit/schema-introspection`
- `POST /api/agents/prompt`

## Security and Governance Notes

- Services own all write logic; routes remain thin wrappers.
- Dynamic JSON payloads are validated against active schema definitions.
- Audit events are emitted on mutation operations.
- Agent orchestration uses governed tools in read-only mode for platform data (no create/update/delete through chat prompts).
- RBAC scaffolding is included for workspace-scoped permission checks.
