# AGENTS.md

## Project

LedgerLens is a read-only search, reporting, and analytics layer for Sage 50 Accounts.

The application synchronizes data from Sage 50 through its read-only ODBC interface into a canonical relational model and search index, then exposes that data through a FastAPI backend and React-Admin frontend.

The project should support multiple Sage 50 schema versions through version-specific adapters.

## Development environment

- Windows 11 is a supported development environment.
- Python dependency and environment management: `uv`
- Python backend: FastAPI
- Database access: SQLModel where practical
- Relational database: PostgreSQL
- Search engine: Typesense
- Frontend: React + TypeScript
- Package manager: `pnpm`
- Admin framework: React-Admin
- Data grid: `ra-devextreme-grid`
  - https://github.com/pjcunningham/ra-devextreme-grid
- Testing:
  - Python: pytest
  - Frontend: Vitest where appropriate

## Architecture

Keep Sage-specific schema details isolated from the rest of the application.

Use a versioned adapter architecture such as:

- Sage v32 adapter
- Sage v33 adapter
- Sage v34 adapter

Each adapter should map Sage data into a canonical accounting domain model.

The rest of the application must depend on the canonical model, not directly on Sage ODBC table names or column names.

Expected canonical concepts include:

- Customer
- Supplier
- Product
- Invoice
- InvoiceLine
- CreditNote
- CreditNoteLine
- Quotation
- QuotationLine
- SalesOrder
- SalesOrderLine
- PurchaseOrder
- Transaction
- NominalAccount
- Department
- Project
- TaxCode

## Data flow

Preferred architecture:

Sage 50
-> read-only ODBC
-> Python synchronization layer
-> PostgreSQL canonical store
-> Typesense search indexes
-> FastAPI
-> React-Admin

PostgreSQL is the canonical synchronized copy.

Typesense is a derived search projection and must be rebuildable from PostgreSQL.

Do not treat Typesense as the authoritative data store.

## Sage access

- Sage access is read-only.
- Do not design features that modify Sage data unless explicitly requested in a future phase.
- Minimize expensive ODBC queries.
- Prefer incremental synchronization where reliable.
- Support full reconciliation where necessary.
- Never assume Sage schemas are identical across versions.

## Frontend

Use React-Admin for the application shell and resource management.

Use `ra-devextreme-grid` instead of AG Grid.

Do not introduce AG Grid.

The UI should use Sage accounting concepts rather than exposing raw database tables.

Primary navigation is expected to include concepts such as:

- Customers
- Suppliers
- Products
- Quotations
- Sales Orders
- Invoices
- Credits
- Transactions

Global search should eventually support federated search across multiple accounting entities.

## Python conventions

- Use modern Python typing.
- Prefer Python 3.14 unless a dependency requires an earlier supported version.
- Use `pathlib` rather than `os.path` where appropriate.
- Prefer dataclasses or Pydantic/SQLModel models over unstructured dictionaries.
- Keep modules small and focused.
- Avoid unnecessary abstractions.
- Use explicit exceptions for domain and synchronization errors.
- Do not silently swallow exceptions.

## TypeScript conventions

- Use TypeScript strictly.
- Avoid `any` unless there is a documented reason.
- Prefer small, typed components and hooks.
- Keep React-Admin integration separate from low-level API client code.

## Testing

All new behavior should have tests where practical.

Before considering a task complete:

1. Run relevant tests.
2. Run lint/type checks where configured.
3. Report any failing tests.
4. Do not claim success if checks have not been run.

Do not delete or weaken existing tests merely to make a change pass.

## Git and scope discipline

- Do not commit changes unless explicitly asked.
- Do not push to GitHub unless explicitly asked.
- Do not make unrelated refactors while implementing a focused phase.
- Preserve public APIs unless a change is required by the plan.
- If a requested change has architectural consequences, explain them before making broad changes.

## Plans

Implementation plans live under:

`.junie/plans/`

When asked to implement a plan:

1. Read the full plan first.
2. Inspect the existing codebase before editing.
3. Follow the plan closely.
4. Do not expand scope without a clear reason.
5. Run the required tests/checks.
6. Summarize:
   - files changed
   - architectural decisions
   - tests added or modified
   - test results
   - anything deferred

## General working style

Prefer simple, maintainable solutions over clever ones.

Do not introduce new dependencies without a clear benefit.

When uncertain about an existing project convention, inspect the repository before inventing a new one.

Do not replace working project patterns merely because another approach is more fashionable.
