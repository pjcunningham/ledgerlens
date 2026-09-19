# LedgerLens

LedgerLens is an early-development, read-only search, reporting, and analytics
layer for Sage 50 Accounts. Phase 001 provides the development foundation and a
temporary synthetic customer grid. Phase 002 adds a separate read-only Sage ODBC
discovery CLI. Synchronization and canonical accounting models are not implemented.

## Architecture

```text
Sage 50 -> read-only ODBC -> versioned Sage adapter -> canonical PostgreSQL model
                                                        |             |
                                                        v             |
                                                     Typesense        |
                                                        |             |
                                                        +-> FastAPI <-+
                                                                |
                                                                v
                                                           React-Admin
```

PostgreSQL will be the authoritative synchronized copy. Typesense is a derived
search projection that must be rebuildable from PostgreSQL. Future versioned
adapters will isolate Sage schema differences from the canonical model.

The backend uses a Python src layout with separate API, configuration, database,
and search modules. FastAPI owns one engine per application lifespan and provides
a new SQLModel session per request/unit of work. Startup does not create tables
or connect to Sage. Alembic owns schema changes; there are no accounting models,
collections, or substantive migrations yet.

The frontend uses React-Admin and
[ra-devextreme-grid](https://github.com/pjcunningham/ra-devextreme-grid).
Its standalone `DatagridDXRemote` resource calls the typed data provider's
`getGrid()` method. The provider owns HTTP transport; FastAPI validates the
request. No `List`/`ListBase` wrapper is used.

LedgerLens intentionally uses React-Admin's light theme because DevExtreme currently
loads `dx.light.css`. Do not enable React-Admin dark mode independently without
adding a matching DevExtreme dark theme.

## Prerequisites

- Windows 11, or a compatible development OS.
- Python 3.14 (uv can install it) and [uv](https://docs.astral.sh/uv/).
- Node.js 24 LTS and pnpm 10.20.0 (recorded in `frontend/package.json`).
- Docker Desktop with Linux containers, or a compatible Docker Engine with Compose.
- An appropriate DevExpress licence for DevExtreme; see the licensing note below.

## Windows / PowerShell setup

From the repository root:

```powershell
Copy-Item .env.example .env
docker compose up -d
docker compose ps

cd backend
uv sync --locked
uv run uvicorn ledgerlens.main:app --reload
```

In a second terminal, from the repository root:

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open <http://localhost:5173> and select **Demo customers**.
The native pager offers 10, 25, 50, or 100 rows. Sorting supports multiple
columns (Shift-click for additional sort keys). Columns can be resized,
reordered, and hidden using the chooser. Column layout is saved locally under
`ledgerlens.demo-customers.layout.v1`.

Development URLs:

| URL | Purpose |
| --- | --- |
| http://localhost:5173 | LedgerLens dashboard and demo grid |
| http://localhost:8000/docs | Interactive API documentation |
| http://localhost:8000/api/health/live | Process liveness, independent of infrastructure |
| http://localhost:8000/api/health/ready | PostgreSQL and Typesense readiness |
| http://localhost:8108/health | Typesense health (default host port) |

Vite forwards same-origin `/api` requests to `http://127.0.0.1:8000`.
Backend and Vite development servers run natively; Compose contains only
PostgreSQL 18.6 and Typesense 30.2.

### Configuration and port conflicts

The backend reads the root `.env` regardless of whether it is launched from the
repository root or `backend/`. Environment variables override the file.
`LEDGERLENS_` variables configure the application. CORS origins are
comma-separated HTTP(S) origins with no trailing slash, path, or wildcard.
Defaults are development-only values; the example contains no production secrets.

Compose binds service ports to loopback and uses named volumes.
If the normal ports are occupied or reserved by Windows, edit the ignored
root `.env` before starting Compose. For example:

```dotenv
POSTGRES_PORT=55432
LEDGERLENS_DATABASE_URL=postgresql+psycopg://ledgerlens:ledgerlens_dev@localhost:55432/ledgerlens
TYPESENSE_PORT=58108
LEDGERLENS_TYPESENSE_PORT=58108
```

Keep the PostgreSQL database/user/password variables and database URL in sync;
keep the Typesense published port and application port in sync. Changing
PostgreSQL initialization credentials does not update an already initialized volume.

Use `docker compose up -d --wait --wait-timeout 120` to wait for both health checks.
The Typesense image has no curl/wget, so its health check uses the included Bash
to request `/health` and verify the healthy response body.

Stop native servers with Ctrl+C. `docker compose down` stops development
infrastructure and retains named data volumes.

## Demo API contract

`POST /api/demo/customers/grid` accepts:

```json
{
  "loadOptions": {
    "skip": 0,
    "take": 25,
    "requireTotalCount": true,
    "sort": [{ "selector": "account_ref", "desc": false }]
  }
}
```

It returns `{"data": [...], "totalCount": 100}`. The count is omitted unless
requested. The backend generates 100 deterministic synthetic rows in memory;
nothing is persisted to PostgreSQL. This is not the final Customer domain model.
Balances are display-only synthetic numbers, not a canonical money representation.

- `skip`: integer 0–1,000,000, default 0.
- `take`: integer 1–100, default 25.
- `requireTotalCount`: boolean, default false.
- `sort`: up to five ordered descriptors; selectors are explicitly whitelisted:
  `id`, `account_ref`, `name`, `balance`, `active`.
- Sort ties use ascending ID for deterministic paging unless ID is explicitly sorted.
- Unknown properties, invalid types, and unsupported operations return HTTP 422.
- An inactive native `filter: null` is accepted; filter expressions are rejected.

The UI does not expose filtering, grouping, summaries, or editing.
Other React-Admin data-provider operations reject explicitly.
Readiness returns HTTP 503 and component states when a required service fails;
responses do not expose dependency exceptions or credentials.

## Quality checks

From `backend/`:

```powershell
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build
```

Unit tests run without Docker. The integration test is opt-in and skipped by
default. With Compose healthy, run:

```powershell
uv run pytest --run-integration -m integration
uv run alembic upgrade head
uv run alembic check
```

The integration test makes real PostgreSQL and Typesense probes through the
FastAPI readiness endpoint. Alembic currently has no substantive revisions.
Future model modules must be imported in `backend/alembic/env.py` before
autogenerating migrations.

To check the running HTTP server from PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/api/health/ready
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/demo/customers/grid -ContentType application/json -Body '{"loadOptions":{"skip":25,"take":10,"requireTotalCount":true}}'
```

From `frontend/`:

```powershell
pnpm install --frozen-lockfile
pnpm lint
pnpm format:check
pnpm typecheck
pnpm test
pnpm build
```

Use `uv run ruff format .` or `pnpm format` to apply formatting.
From the root, validate infrastructure with `docker compose config --quiet`.

GitHub Actions runs Linux backend quality/package checks, Windows backend unit
tests, frontend quality/build checks, and a real Linux Compose readiness smoke
test. No Sage installation or private credentials are required.

## Sage discovery (Phase 002)

Real discovery requires Windows, a matching 64-bit Sage 50 Accounts ODBC driver,
and a System DSN configured for the company. Sage v28.1+ DSNs normally point at
the company's `ACCDATA` directory. Configure the DSN in Windows ODBC Data Source
Administrator; LedgerLens does not create DSNs or access company files directly.
The normal web application needs neither Sage configuration nor pyodbc.

From `backend/`, install the optional extra with `uv sync --locked --extra sage`.
Set the `LEDGERLENS_SAGE_*` placeholders in the ignored root `.env`, then run:

```powershell
uv run --extra sage ledgerlens-sage drivers
uv run --extra sage ledgerlens-sage probe --sage-version 34.0.23.0 --sage-build 34.0.23.0 --output ../artifacts/sage/local-v34
uv run --extra sage ledgerlens-sage schema --sage-version 34.0.23.0 --sage-build 34.0.23.0 --output ../artifacts/sage/local-v34
uv run --extra sage ledgerlens-sage report --output ../artifacts/sage/local-v34 --sanitized
```

Use your actual Help > About version/build rather than assuming the example matches.
The CLI also provides `describe-table`, `capabilities`, `profile`, `relationships`,
and `benchmark`. Every command has `--help`. Raw metadata and aggregate artifacts
stay in ignored `artifacts/sage/`; no business records are exported. Benchmarks
are explicit and sequential. See [the discovery guide](docs/sage/README.md) for
bounds, timeout limitations, commands, and live findings.

Sage integration tests are opt-in; never configure Sage credentials in hosted CI:

```powershell
uv run --extra sage pytest --run-sage-integration -m sage_integration
```

## Repository layout

```text
.github/workflows/ci.yml
.junie/plans/001-project-foundation.md
backend/
  alembic/                 # migration environment; no accounting tables
  src/ledgerlens/
    api/routes/            # health and temporary demo endpoints
    db/                    # engine and session dependency
    search/                # Typesense client
    config.py
    main.py
  tests/                   # isolated unit tests and opt-in infrastructure test
  alembic.ini
  pyproject.toml
  uv.lock
frontend/
  src/
    api/                   # transport and typed grid data provider
    app/                   # dashboard
    components/            # readiness display
    resources/demo-customers/
    test/
    App.tsx
    main.tsx
  package.json
  pnpm-lock.yaml
  tsconfig.json
  vite.config.ts
.env.example
compose.yml
AGENTS.md
README.md
```

## DevExtreme licensing

`ra-devextreme-grid` is a separate open-source project. DevExtreme itself is
commercially licensed software. Users are responsible for holding the appropriate
DevExpress licence. No DevExpress licence keys or proprietary licence material
are stored in LedgerLens. No LedgerLens repository licence is added by this phase.

## Scope of this foundation

Sage adapters, canonical accounting schemas, synchronization, accounting search
collections, advanced remote queries, authentication, application reporting, and
production deployment remain deferred. Phase 002 discovery supplies evidence
for later decisions; it does not implement these features.
