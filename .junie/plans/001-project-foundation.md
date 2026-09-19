# Phase 001 — Project Foundation

## Status

Planned.

## Objective

Establish a clean, tested development foundation for LedgerLens.

LedgerLens is intended to become a read-only search, reporting, and analytics layer over Sage 50 Accounts. It will eventually synchronize Sage data through the read-only Sage ODBC interface into a canonical relational model, build search projections in Typesense, and expose the data through a FastAPI API and React-Admin frontend.

This phase must establish the application architecture and development tooling without implementing Sage-specific functionality.

At the end of this phase, a developer must be able to clone the repository on Windows 11, start PostgreSQL and Typesense with Docker, run the FastAPI backend, run the React-Admin frontend, and see a working `ra-devextreme-grid` remote grid populated through the FastAPI API.

The repository must also have automated tests, linting, type checking, build checks, and GitHub Actions CI.

---

# 1. Read project instructions first

Before making changes:

1. Read the root `AGENTS.md` completely.
2. Inspect the existing repository.
3. Read this entire plan before implementing anything.
4. Inspect the public `ra-devextreme-grid` repository and its current README, particularly the `DatagridDXRemote` API and FastAPI reference example:

   * https://github.com/pjcunningham/ra-devextreme-grid
5. Do not make assumptions about APIs that can be confirmed from the installed package or its repository.

Do not commit or push changes unless explicitly instructed.

---

# 2. Fixed technology decisions

Use the following stack.

## Backend

* Python 3.14
* `uv` for Python project and dependency management
* FastAPI
* Pydantic v2
* SQLModel
* SQLAlchemy through SQLModel where practical
* PostgreSQL
* Psycopg 3 PostgreSQL driver
* Alembic for schema migrations
* Typesense Python client
* `pydantic-settings` for application configuration
* pytest
* Ruff
* mypy

The backend must use a `src` layout.

Do not use Poetry, pipenv, conda, requirements.txt as the primary dependency mechanism, Django, Flask, or an alternative ORM.

## Frontend

* React
* TypeScript
* Vite
* React-Admin
* MUI as supplied by React-Admin
* DevExtreme React
* `ra-devextreme-grid`
* pnpm
* Vitest
* React Testing Library where appropriate
* ESLint
* Prettier

Do not introduce AG Grid.

Use `ra-devextreme-grid` for LedgerLens data grids.

The initial dependency baseline should remain compatible with the current tested `ra-devextreme-grid` 0.1.x stack. Prefer:

* React 19.x
* React-Admin 5.15.x
* DevExtreme 26.1.x
* DevExtreme React 26.1.x
* `ra-devextreme-grid` 0.1.x

Use lockfiles to record the exact resolved versions.

Do not silently substitute another grid package if `ra-devextreme-grid` installation fails.

## Infrastructure

Use Docker Compose for development infrastructure only.

Initial services:

* PostgreSQL 18.6
* Typesense 30.2

The FastAPI and Vite development servers should run natively during development rather than inside Docker.

---

# 3. Architectural decisions

The intended long-term data flow is:

```text
Sage 50
   |
   | read-only ODBC
   v
Sage version adapter
   |
   v
Canonical accounting model
   |
   v
PostgreSQL
   |
   +--------> Typesense search projections
   |
   v
FastAPI
   |
   v
React-Admin
```

PostgreSQL will become the authoritative synchronized copy of Sage data.

Typesense is a derived search index and must eventually be completely rebuildable from PostgreSQL.

Sage-specific schema details must not leak into the frontend or generic application layers.

No Sage implementation is required in this phase.

---

# 4. Repository structure

Create approximately the following structure:

```text
ledgerlens/
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── .junie/
│   └── plans/
│       └── 001-project-foundation.md
│
├── backend/
│   ├── alembic/
│   ├── src/
│   │   └── ledgerlens/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       ├── config.py
│   │       │
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   ├── router.py
│   │       │   └── routes/
│   │       │       ├── __init__.py
│   │       │       ├── health.py
│   │       │       └── demo.py
│   │       │
│   │       ├── db/
│   │       │   ├── __init__.py
│   │       │   ├── engine.py
│   │       │   └── session.py
│   │       │
│   │       └── search/
│   │           ├── __init__.py
│   │           └── client.py
│   │
│   ├── tests/
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── uv.lock
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── resources/
│   │   │   └── demo-customers/
│   │   ├── api/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── .env.example
├── .gitignore
├── AGENTS.md
├── compose.yml
└── README.md
```

Small deviations are acceptable when they clearly improve the implementation, but do not create unnecessary abstraction layers.

Do not create separate `sync-agent`, `sage-adapters`, `reporting`, or commercial-edition applications in this phase.

---

# 5. Backend project

Create `backend/pyproject.toml` as a proper uv-managed Python project.

Require Python 3.14.

Use an installable package named `ledgerlens`.

Add the runtime dependencies necessary for:

* FastAPI
* application server
* SQLModel
* PostgreSQL
* Alembic
* application configuration
* Typesense

Add development dependencies for:

* pytest
* HTTP/API testing
* Ruff
* mypy
* coverage if useful

Generate and commit `backend/uv.lock`.

Do not manually maintain a duplicate `requirements.txt`.

---

# 6. Application configuration

Implement configuration using `pydantic-settings`.

Configuration must come from environment variables.

Use a consistent `LEDGERLENS_` prefix for application-specific variables.

The root `.env.example` should include development examples for at least:

```text
LEDGERLENS_ENV=development

LEDGERLENS_DATABASE_URL=postgresql+psycopg://ledgerlens:ledgerlens_dev@localhost:5432/ledgerlens

LEDGERLENS_TYPESENSE_HOST=localhost
LEDGERLENS_TYPESENSE_PORT=8108
LEDGERLENS_TYPESENSE_PROTOCOL=http
LEDGERLENS_TYPESENSE_API_KEY=ledgerlens-development-key

LEDGERLENS_CORS_ORIGINS=http://localhost:5173

POSTGRES_DB=ledgerlens
POSTGRES_USER=ledgerlens
POSTGRES_PASSWORD=ledgerlens_dev
```

A real `.env` file must remain ignored by Git.

Do not commit production credentials, API keys, certificates, passwords, DevExpress licence information, or other secrets.

Settings should be validated at startup where practical and have useful error messages.

---

# 7. PostgreSQL foundation

Create a SQLModel/SQLAlchemy engine from configuration.

Provide a reusable FastAPI session dependency.

Use one application engine and create a new session for each request or unit of work.

Do not call `SQLModel.metadata.create_all()` automatically during normal application startup.

Database schema changes must eventually be managed through Alembic.

Configure Alembic correctly for the SQLModel metadata and PostgreSQL connection.

There are no real accounting tables in this phase, so do not invent Customer, Invoice, Supplier, Product, or other domain schemas yet merely to exercise Alembic.

It is acceptable for this phase to contain no substantive database migration.

---

# 8. Typesense foundation

Create a small Typesense client factory/service using application settings.

Do not create accounting collections yet.

Do not introduce search schemas merely to demonstrate Typesense.

The Typesense integration in this phase exists only to establish connectivity and readiness checking.

Typesense must not be treated as an authoritative datastore.

---

# 9. Health endpoints

Implement:

```text
GET /api/health/live
GET /api/health/ready
```

## `/api/health/live`

This is a process liveness endpoint.

It must not depend on PostgreSQL or Typesense.

Example response:

```json
{
  "status": "ok"
}
```

## `/api/health/ready`

This checks required infrastructure.

It should verify at least:

* PostgreSQL connectivity using a lightweight query such as `SELECT 1`
* Typesense health/connectivity

A successful response should make component state clear, for example:

```json
{
  "status": "ready",
  "components": {
    "postgresql": "ok",
    "typesense": "ok"
  }
}
```

If a required component is unavailable, return HTTP 503 with a useful but non-sensitive response.

Do not expose passwords, connection strings, stack traces, or secrets.

---

# 10. FastAPI application structure

Use a FastAPI application factory or similarly clean structure.

Prefer current FastAPI lifespan handling rather than deprecated startup/event patterns where appropriate.

Mount application routes below:

```text
/api
```

Configure development CORS using settings.

Do not enable unrestricted `*` CORS by default.

Automatic OpenAPI documentation should remain available during development.

Expected development URLs include:

```text
http://localhost:8000/docs
http://localhost:8000/api/health/live
http://localhost:8000/api/health/ready
```

---

# 11. `ra-devextreme-grid` architectural choice

Use `DatagridDXRemote` as the default LedgerLens grid architecture.

The reason is that future LedgerLens resources may contain hundreds of thousands or millions of accounting records and will require:

* server-side paging
* multi-column sorting
* server-side filtering
* grouping
* summaries
* deterministic queries

Do not wrap `DatagridDXRemote` in React-Admin `<List>` or `<ListBase>`.

Use the `DatagridDXDataProvider` / `getGrid()` contract supplied by `ra-devextreme-grid`.

The frontend owns transport.

The backend owns query validation and eventual translation to safe database operations.

Do not implement the full production remote-filter compiler in this phase.

The `ra-devextreme-grid` FastAPI example may be studied for architecture and request/response semantics, but do not blindly copy the entire example into LedgerLens.

---

# 12. Foundation demo resource

Create one explicitly temporary resource named something similar to:

```text
demo-customers
```

This resource exists solely to prove the complete browser-to-FastAPI `DatagridDXRemote` path.

It must not be presented as the final LedgerLens Customer domain model.

Use deterministic synthetic data generated by the backend.

For example, approximately 50–100 demo rows with fields such as:

```text
id
account_ref
name
balance
active
```

Do not persist these rows in PostgreSQL.

Expose:

```text
POST /api/demo/customers/grid
```

using a request body compatible with the subset of `getGrid()` load options required by the demo.

At minimum support:

* `skip`
* `take`
* `requireTotalCount`
* basic whitelisted sorting if straightforward

The response should follow the `ra-devextreme-grid` remote result contract:

```json
{
  "data": [],
  "totalCount": 100
}
```

Validate paging boundaries.

Never dynamically evaluate client-provided field names.

If sorting is implemented, selectors must be mapped through an explicit whitelist.

Do not implement arbitrary filtering, grouping, summaries, SQL expression compilation, or dynamic attribute access in this phase.

---

# 13. React application

Create a Vite React + TypeScript frontend.

Enable strict TypeScript.

Use React-Admin as the application shell.

The initial application should visibly identify itself as:

```text
LedgerLens
```

Provide a minimal dashboard containing:

* application name
* development/foundation status
* backend readiness state if practical
* navigation to the demo grid

No attempt should be made to clone Sage's visual styling in this phase.

The long-term goal is to use Sage accounting concepts and workflow familiarity, not to copy Sage's proprietary UI pixel-for-pixel.

---

# 14. React data provider

Implement a typed LedgerLens data provider.

It must implement or extend the `DatagridDXDataProvider` contract.

The important foundation method is:

```text
getGrid(resource, params)
```

Map known resources explicitly to backend endpoints.

For the demo:

```text
demo-customers
    ->
POST /api/demo/customers/grid
```

Do not construct arbitrary backend URLs directly from untrusted resource names.

Other React-Admin DataProvider methods may be minimal in this phase, but their unsupported state should be explicit rather than returning misleading fake success responses.

Do not introduce a generic CRUD abstraction before real domain resources exist.

---

# 15. Demo grid

Use `DatagridDXRemote` for the demo resource.

Display columns such as:

```text
Account
Customer Name
Balance
Active
```

Enable:

* remote paging
* native pager
* sensible page-size choices
* column resizing
* column reordering
* column chooser if supported cleanly
* layout persistence using a LedgerLens-specific `layoutPreferenceKey`

Do not enable features that the Phase 001 backend does not support.

In particular, do not expose a Filter Row, grouping UI, summaries, or other server operations until the backend implements their semantics safely.

Import an appropriate DevExtreme stylesheet at the application root.

Do not introduce AG Grid as a fallback.

---

# 16. Vite development proxy

Configure Vite so frontend development can call:

```text
/api/...
```

and proxy those requests to the FastAPI development server, normally:

```text
http://127.0.0.1:8000
```

Application code should therefore use same-origin-style API paths rather than hard-coded FastAPI hostnames.

This will simplify eventual Nginx deployment.

---

# 17. Docker Compose

Create a root `compose.yml`.

It should contain development services for:

```text
postgres
typesense
```

Use:

```text
PostgreSQL 18.6
Typesense 30.2
```

Use named persistent volumes.

Provide health checks where practical.

Use environment variables for credentials and Typesense API key.

Expose the normal development ports:

```text
PostgreSQL 5432
Typesense 8108
```

Allow ports to be overridden through environment variables if this can be done without unnecessary complexity.

Do not containerize the FastAPI or React development servers in this phase.

A developer should be able to run:

```powershell
docker compose up -d
```

and obtain the required application infrastructure.

---

# 18. Backend tests

Add focused automated tests.

At minimum test:

### Health

* liveness returns 200 without infrastructure
* readiness returns 200 when dependency checks succeed
* readiness returns 503 when PostgreSQL is unavailable
* readiness returns 503 when Typesense is unavailable
* readiness responses do not expose secrets

### Configuration

* required settings are parsed correctly
* invalid settings fail clearly where appropriate

### Demo grid

* first page
* subsequent page
* requested page size
* total count
* end-of-data behavior
* invalid negative paging values
* excessive or invalid paging inputs
* permitted sorting if sorting is implemented
* unknown sort selectors are rejected

Use dependency injection or mocking where appropriate so most tests do not require Docker services.

Also provide at least one infrastructure smoke/integration test or documented command proving real PostgreSQL and Typesense connectivity.

---

# 19. Frontend tests

Add practical tests without over-testing framework internals.

At minimum cover:

* application renders
* LedgerLens title is present
* demo resource is registered
* `getGrid()` calls the expected backend endpoint
* load options are sent correctly
* returned remote result is passed through correctly
* API/network failures surface as rejected operations rather than silently succeeding

Run:

* lint
* TypeScript type checking
* Vitest
* production Vite build

Do not add Playwright unless it provides clear value for this phase.

The `ra-devextreme-grid` project already has its own browser-level coverage; LedgerLens browser E2E tests can be introduced when real resources exist.

---

# 20. Formatting and quality

Backend:

```text
Ruff
mypy
pytest
```

Frontend:

```text
ESLint
Prettier
TypeScript compiler
Vitest
Vite production build
```

Avoid disabling rules merely to make CI green.

Avoid broad `# type: ignore`, `Any`, `eslint-disable`, and equivalent escape hatches without a documented reason.

---

# 21. GitHub Actions CI

Create:

```text
.github/workflows/ci.yml
```

CI should run automatically for pushes and pull requests.

At minimum include:

## Backend quality job

On Linux:

* install Python 3.14
* install uv
* `uv sync`
* Ruff
* mypy
* pytest

## Windows backend smoke job

Because Sage integration will eventually make Windows a first-class environment:

* Windows runner
* Python 3.14
* uv
* install backend
* run backend unit tests

This job does not need Sage or Docker.

## Frontend job

* supported Node LTS
* pnpm
* frozen lockfile install
* lint
* typecheck
* tests
* production build

## Infrastructure validation

At minimum:

```text
docker compose config
```

Ideally also provide a lightweight Linux CI smoke check proving PostgreSQL and Typesense containers can start successfully.

Do not make CI depend on private credentials.

---

# 22. README

Create a useful root `README.md`.

It should contain:

## Project purpose

Explain briefly that LedgerLens is intended to provide fast, read-only search, reporting, and analytics over Sage 50 data.

State clearly that the current repository is in early development.

## Architecture

Document the intended flow:

```text
Sage 50 -> ODBC -> canonical PostgreSQL model -> Typesense -> FastAPI -> React-Admin
```

Clarify that Sage synchronization is not implemented in Phase 001.

## Development prerequisites

At least:

* Windows 11 or supported development OS
* Python 3.14
* uv
* Node
* pnpm
* Docker Desktop or compatible Docker environment

## Setup

For Windows/PowerShell provide commands covering:

```powershell
Copy-Item .env.example .env

docker compose up -d

cd backend
uv sync
uv run uvicorn ledgerlens.main:app --reload
```

and separately:

```powershell
cd frontend
pnpm install
pnpm dev
```

Document the local URLs.

## Quality commands

Document how to run backend and frontend checks.

## DevExtreme licensing

State clearly that:

* `ra-devextreme-grid` is a separate open-source project.
* DevExtreme itself is commercially licensed software.
* Users are responsible for holding the appropriate DevExpress licence.
* No DevExpress licence keys or proprietary licence material are stored in LedgerLens.

Do not make broader legal claims.

Do not add or change the LedgerLens repository licence in this phase unless explicitly instructed. Open-core/community/commercial licensing needs a separate deliberate decision.

---

# 23. `.gitignore`

Review the existing `.gitignore` and update it only as required.

Ensure at minimum that the following remain ignored:

* Python virtual environments
* Python caches
* test caches
* frontend `node_modules`
* frontend build output
* local `.env`
* local databases
* logs
* PyCharm local project metadata where appropriate
* `.codex/config.toml`
* secrets and certificates

Do not ignore:

```text
backend/uv.lock
frontend/pnpm-lock.yaml
AGENTS.md
.junie/plans/
.env.example
```

---

# 24. Explicitly out of scope

Do not implement any of the following in Phase 001:

* Sage ODBC connectivity
* pyodbc
* Sage schema discovery
* Sage version detection
* Sage version adapters
* customers as a real canonical model
* suppliers
* products
* invoices
* credits
* quotations
* sales orders
* purchase orders
* Sage transactions
* synchronization engine
* incremental synchronization
* deletion reconciliation
* Typesense accounting collections
* global search
* authentication
* authorization
* SSO
* Microsoft Entra ID
* audit logging
* reporting
* DevExpress Reports
* PDF generation
* scheduled reports
* dashboards containing real accounting metrics
* historical snapshots
* alerts
* billing/licensing enforcement
* commercial-edition code
* Redis
* Celery or another task queue
* Kubernetes
* production deployment
* Nginx
* HTTPS
* arbitrary remote grid filtering
* remote SQL filter compilation
* remote grouping
* group paging
* remote summaries
* AG Grid

Avoid speculative infrastructure for future phases.

---

# 25. Acceptance criteria

Phase 001 is complete only when all of the following are true.

### Repository

* backend and frontend projects exist
* lockfiles are committed
* project structure is clean and documented
* no secrets are committed

### Infrastructure

From the repository root:

```powershell
docker compose up -d
```

starts healthy PostgreSQL and Typesense services.

### Backend

The backend can be installed with:

```powershell
cd backend
uv sync
```

and started with:

```powershell
uv run uvicorn ledgerlens.main:app --reload
```

The following work:

```text
GET /docs
GET /api/health/live
GET /api/health/ready
POST /api/demo/customers/grid
```

### Backend quality

These complete successfully:

```powershell
uv run ruff check .
uv run mypy src
uv run pytest
```

### Frontend

The frontend can be installed with:

```powershell
cd frontend
pnpm install
```

and started with:

```powershell
pnpm dev
```

The browser displays LedgerLens and the demo customer grid.

The grid retrieves its rows through:

```text
React-Admin
 -> DatagridDXRemote
 -> getGrid()
 -> FastAPI
```

and not from a hard-coded frontend array.

Paging works.

### Frontend quality

The appropriate equivalents of these commands succeed:

```text
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

### CI

GitHub Actions passes for:

* backend checks
* Windows backend smoke tests
* frontend checks
* infrastructure configuration/smoke checks

---

# 26. Implementation discipline

Keep this phase focused.

Do not add abstractions merely because they may be useful later.

However, do preserve the following architectural boundaries:

```text
API
Database
Search
Configuration
Frontend transport
Frontend resources
```

Do not put all backend logic into `main.py`.

Do not put all frontend logic into `App.tsx`.

Do not create a generic repository/service framework before actual domain requirements justify one.

Prefer straightforward typed code.

---

# 27. Completion report

When implementation is finished, report:

1. Summary of what was implemented.
2. Final repository structure.
3. Important architectural decisions made.
4. Dependencies added.
5. Files created or significantly modified.
6. Tests added.
7. Exact backend test/lint/type-check results.
8. Exact frontend test/lint/type-check/build results.
9. Docker/infrastructure smoke-test results.
10. GitHub Actions configuration added.
11. Any deviations from this plan and why.
12. Anything intentionally deferred to Phase 002.

Do not claim that a check passed unless it was actually executed.

Do not commit or push the implementation unless explicitly instructed.
