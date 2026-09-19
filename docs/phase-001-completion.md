# Phase 001 implementation and completion report

Date: 2026-09-19

Implementation is finished and the checks listed below passed locally. Full
acceptance remains unverified for the rendered browser grid and hosted GitHub
Actions. No commit or push was performed; both generated lockfiles are present
as uncommitted repository files, as requested.

## 1. Summary

Implemented the FastAPI backend, strict TypeScript React-Admin frontend, real
`DatagridDXRemote` integration, deterministic synthetic customer grid API,
PostgreSQL/Typesense development infrastructure, dependency lockfiles, tests,
quality tooling, GitHub Actions, and Windows setup documentation.

The root instructions and full Phase 001 plan were read before implementation.
The public ra-devextreme-grid README, local reference FastAPI example, and
installed 0.1.0 type declarations were inspected.

## 2. Final repository structure

```text
ledgerlens/
  .github/workflows/ci.yml
  .junie/plans/001-project-foundation.md
  backend/
    alembic/
      env.py
      script.py.mako
      versions/.gitkeep
    src/ledgerlens/
      __init__.py
      api/
        __init__.py
        router.py
        routes/
          __init__.py
          health.py
          demo.py
      db/
        __init__.py
        engine.py
        session.py
      search/
        __init__.py
        client.py
      config.py
      main.py
    tests/
      conftest.py
      test_config.py
      test_demo.py
      test_health.py
      test_infrastructure.py
    alembic.ini
    pyproject.toml
    uv.lock
  frontend/
    src/
      api/
        http.ts
        dataProvider.ts
        dataProvider.test.ts
      app/Dashboard.tsx
      components/BackendReadiness.tsx
      resources/demo-customers/DemoCustomerList.tsx
      test/setup.ts
      App.tsx
      App.test.tsx
      main.tsx
    .prettierignore
    .prettierrc.json
    eslint.config.js
    index.html
    package.json
    pnpm-lock.yaml
    tsconfig.json
    vite.config.ts
  docs/phase-001-completion.md
  .env.example
  .gitignore
  AGENTS.md
  compose.yml
  README.md
```

Ignored local artifacts include the virtual environment, node_modules, build
outputs, caches, and a development .env with local port overrides.

## 3. Architectural decisions

- PostgreSQL is the future canonical synchronized store. Typesense remains a
  rebuildable search projection. No accounting schemas or collections were invented.
- A FastAPI application factory and lifespan own one database engine and search
  client. SQLModel sessions are created per request/unit of work. No startup
  `create_all()` is used; Alembic is configured against SQLModel metadata.
- Pydantic settings use the LEDGERLENS_ prefix, load the root .env, validate URL,
  port, protocol, credentials, and CORS inputs, and redact secret representations.
- Liveness does not probe infrastructure. Readiness performs SELECT 1 and the
  installed Typesense client's `operations.is_healthy()` call. Failed components
  produce HTTP 503 with safe component states.
- The demo uses 100 immutable synthetic rows in backend memory. Paging is strictly
  bounded; sorting maps five allowed fields to explicit functions. Stable sorting
  preserves an ID tie-breaker. No client selectors are evaluated dynamically.
- The wire envelope is `{loadOptions: {...}}`. Counts are returned only when
  requested. An inactive `filter: null` is accepted, but filter expressions,
  grouping, and summaries are rejected.
- The standalone remote grid uses native paging and explicit supported controls.
  It is not inside List/ListBase. The typed data provider explicitly maps the
  demo resource, uses same-origin API paths, and rejects unsupported CRUD.
- React-Admin explicitly uses `theme={defaultLightTheme}`, matching the reference
  application and DevExtreme's `dx.light.css`. This fixes the pager visibility
  issue caused by React-Admin selecting dark mode while DevExtreme retained light
  styling. No pager-specific CSS overrides were added.
- Compose runs infrastructure only, with loopback ports and named persistent
  volumes. Development application servers remain native.

## 4. Dependencies added

Exact transitive resolutions are in backend/uv.lock and frontend/pnpm-lock.yaml.

Backend direct runtime dependencies:

| Dependency | Resolved version |
| --- | --- |
| FastAPI | 0.141.1 |
| Uvicorn (standard extras) | 0.53.0 |
| Pydantic | 2.13.5 |
| pydantic-settings | 2.15.0 |
| SQLModel | 0.0.42 |
| Psycopg / psycopg-binary | 3.3.6 |
| Alembic | 1.20.0 |
| Typesense | 1.3.0 |

SQLAlchemy 2.0.54 is supplied through SQLModel. Backend development dependencies
are pytest 9.1.1, HTTPX 0.28.1, Ruff 0.16.8, and mypy 1.20.2.

Frontend runtime dependencies: React and React DOM 19.3.0, React-Admin 5.15.3,
DevExtreme and DevExtreme React 26.1.5, ra-devextreme-grid 0.1.0, MUI material
and icons 7.3.11, Emotion React 11.14.0 / styled 11.14.1, and React Router DOM
7.18.4. MUI icons are explicitly constrained to the same major as MUI material
to avoid the loose upstream dependency resolving an incompatible major.

Frontend development dependencies include Vite 7.3.6, its React plugin 5.2.0,
TypeScript 5.8.3, Vitest 3.2.7, React Testing Library 16.3.3, jest-dom 6.9.1,
jsdom 26.1.0, ESLint 9.39.5, typescript-eslint 8.70.0, React Hooks ESLint plugin
5.2.0, eslint-config-prettier 10.1.8, Prettier 3.9.8, globals 16.5.0, and
Node/React/React DOM type packages.

No AG Grid, Sage/ODBC dependency, Playwright dependency, authentication, task queue,
or production infrastructure was added.

## 5. Files created or significantly modified

All backend, frontend, infrastructure, CI, README, .env.example, and report files
shown above were created. The plan status was updated to reference this report
and the remaining verification limits.

AGENTS.md was preserved. The existing .gitignore was reviewed and already covered
the required local artifacts, secrets, certificates, and editor metadata. No
repository licence was added or modified.

## 6. Tests added

- Configuration: 12 tests covering environment parsing, secret redaction, invalid
  database URLs, ports, protocols, keys, environments, and CORS origins.
- Demo API: 37 tests covering first/subsequent pages, page sizes, counts,
  end-of-data, strict input rejection, supported sort fields/directions,
  stable tie-breaks, multi-sort, the request envelope, and inactive native filters.
- Health: 10 tests covering infrastructure-independent liveness, every readiness
  combination, actual probe error handling without leaking secrets, unhealthy
  Typesense responses, OpenAPI documentation, and scoped CORS.
- Infrastructure: one opt-in integration test that uses real PostgreSQL and
  Typesense through FastAPI readiness.
- Frontend: 11 transport tests covering endpoint mapping, body serialization,
  result pass-through, unknown resources, HTTP/network/malformed-response failures,
  and unsupported CRUD; four React-Admin application/theme-related tests covering
  title, dashboard, registered demo navigation, readiness success/failure, and
  light-theme behavior under system-dark and saved-dark preferences. The two theme
  regression cases failed before the fix and passed afterward, bringing the
  frontend total to 15 tests.

The app tests render the real React-Admin shell with the vendor grid page stubbed
and a dashboard wrapper observing MUI's public theme API. They do not assert CSS
implementation details or substitute for browser validation of the actual grid.

## 7. Exact backend check results

Executed on Windows with Python 3.14.3 and uv 0.10.9:

| Command (backend/) | Final result |
| --- | --- |
| `uv sync --locked` | PASS; 48 packages resolved, 47 installed packages audited |
| `uv run ruff check .` | PASS; All checks passed |
| `uv run ruff format --check .` | PASS; 19 files already formatted |
| `uv run mypy src` | PASS; no issues in 13 source files |
| `uv run pytest` | PASS; 59 passed, 1 intentionally skipped, 49 warnings, 0.46 seconds |
| `uv run pytest --run-integration -m integration` | PASS; 1 passed, 59 deselected, 3 warnings, 5.17 seconds |
| `uv run alembic upgrade head` | PASS; exit 0, no substantive migrations |
| `uv run alembic check` | PASS; No new upgrade operations detected |
| `uv build` | PASS; source archive and wheel generated |

Warnings originate from dependency deprecations in Starlette/HTTPX/AnyIO and the
Typesense client's internal AnalyticsV1 construction. They were not suppressed.
There are no remaining failing backend tests.

## 8. Exact frontend check results

Executed with Node 24.14.1 and pnpm 10.20.0:

Lint, formatting, type checking, tests, and the production build were rerun after
the explicit `defaultLightTheme` fix. The results below reflect that run; install
and esbuild rebuild results are retained from the foundation checks.

| Command (frontend/) | Final result |
| --- | --- |
| `pnpm install --frozen-lockfile` | PASS; lockfile current |
| `pnpm lint` | PASS; exit 0 |
| `pnpm format:check` | PASS; all matched files use Prettier style |
| `pnpm typecheck` | PASS; tsc --noEmit, exit 0 |
| `pnpm test` | PASS; 2 files, 15 tests passed, 3.55 seconds |
| `pnpm build` | PASS; 3,333 modules transformed, built in 6.58 seconds |
| `pnpm rebuild esbuild` | PASS; standard esbuild install check |

Vite reports its default large-chunk advisory: the combined JS is 3,167.91 kB
(901.06 kB gzip), and CSS is 693.40 kB (96.25 kB gzip). The warning was not hidden.
Bundle optimization is not a Phase 001 acceptance requirement.

Dependency installation also reports deprecated ESLint 9 and transitive package
notices. The initial ignored esbuild build-script warning was followed by an
explicit successful rebuild; package configuration permits esbuild's script.
There are no remaining failing frontend tests.

## 9. Docker and infrastructure smoke results

- Started Docker Desktop and pulled the requested postgres:18.6 and
  typesense/typesense:30.2 images.
- `docker compose config --quiet`: PASS.
- `docker compose up -d --wait --wait-timeout 60`: PASS.
- `docker compose ps`: both services healthy.
- Real integration readiness test: PASS.
- Live HTTP liveness: `{"status":"ok"}`.
- Live HTTP readiness:
  `{"status":"ready","components":{"postgresql":"ok","typesense":"ok"}}`.
- Live `GET /docs`: HTTP 200.
- Live POST through the Vite proxy on port 5173, skip 25 / take 10: ten rows,
  first ID 26, last ID 35, totalCount 100.

Local port 5432 was blocked by Windows, and 8108 was already in use. The ignored
.env uses PostgreSQL 55432 and Typesense 58108; tracked defaults remain 5432/8108.
Existing services were not stopped.

The official Typesense image has no curl/wget. Its health check uses its existing
Bash to make an HTTP request and verify the health response; no custom image or
extra service was introduced.

Native servers were started for the HTTP checks. Browser automation was attempted,
but Computer Use stopped because it could not determine the Windows browser URL
confidently enough to enforce policy. UI automation was stopped; visual rendering,
interactive native paging, and layout persistence were not manually confirmed.
This is an outstanding acceptance verification, not a passing browser check.

## 10. GitHub Actions configuration

.github/workflows/ci.yml runs on pushes and pull requests, with read-only
repository permissions and four jobs:

1. Linux backend: Python 3.14, uv locked install, Ruff lint/format, mypy, pytest,
   and Python package build.
2. Windows backend smoke: Python 3.14, uv locked install, and unit tests without
   Docker or Sage.
3. Frontend: Node 24, pnpm frozen install, ESLint, Prettier, TypeScript, Vitest,
   and Vite build.
4. Linux infrastructure: Compose validation/startup, actual backend readiness
   integration test, Alembic upgrade, failure diagnostics, and cleanup.

Hosted GitHub Actions was not executed because this task explicitly prohibits
committing or pushing. No hosted CI success is claimed.

## 11. Deviations and verification limits

- Lockfiles were generated but not committed, honoring the user's explicit
  no-commit/no-push instruction over the plan's lockfile-commit wording.
- Local port overrides were necessary for existing Windows port conflicts.
- Added a completion-report artifact and recorded implementation status in the plan.
- No substantive migration was added, as explicitly allowed by the plan.
- Browser acceptance and hosted CI remain unverified for the reasons above.
- No new feature scope or alternative grid was introduced.

Initial lint/test issues and the first Typesense health-check command were fixed.
Final required local automated checks passed. Do not interpret this report as
proof that every acceptance criterion, especially browser and hosted CI, was met.

## 12. Intentionally deferred to Phase 002 or a later scoped plan

Sage ODBC access and versioned adapters, canonical accounting models, synchronization,
Typesense accounting indexes/global search, arbitrary remote filtering/grouping/
summaries, authentication/authorization, reporting, and production deployment.

No claims are made about which of those features Phase 002 will select. That phase
needs a deliberate implementation plan. The remaining Phase 001 browser/hosted CI
verification should be completed before declaring full acceptance.
