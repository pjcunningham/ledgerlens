# Phase 002 — Sage 50 Accounts v34 ODBC Discovery

## Status

Planned.

## Objective

Build a safe, reproducible discovery and profiling toolkit for the Sage 50 Accounts v34 ODBC interface.

This phase must establish, from real Sage data and driver metadata:

* what tables Sage exposes;
* what columns and ODBC types they contain;
* what metadata the driver provides;
* which fields appear to be identifiers and relationships;
* how Sage's documented relationships behave against real data;
* what SQL capabilities the ODBC driver supports;
* how expensive representative read operations are;
* which tables and fields are likely to matter to LedgerLens;
* what information is needed to design the canonical accounting model in Phase 003.

This phase is **discovery**, not synchronization.

Do not build Customer, Invoice, Product, Supplier, or other canonical LedgerLens models yet.

The result of Phase 002 should be evidence that Phase 003 can use to design those models.

---

# 1. Read existing project material first

Before changing code:

1. Read `AGENTS.md`.
2. Read `.junie/plans/001-project-foundation.md`.
3. Read `docs/phase-001-completion.md`.
4. Inspect the current backend structure and configuration implementation.
5. Read this entire plan.
6. Inspect the official Sage 50 Accounts ODBC documentation relevant to v34.
7. Do not make changes until the existing project conventions are understood.

Do not commit or push unless explicitly instructed.

---

# 2. Sage facts and assumptions

The initial discovery target is:

```text
Sage 50 Accounts v34.x
64-bit ODBC driver
Windows 11
64-bit Python 3.14
```

However, do not assume that:

```text
v34.0 == v34.1
```

or that different v34 builds expose an identical schema.

Record the exact environment used for every discovery run.

Sage's ODBC interface is read-only.

LedgerLens must never attempt INSERT, UPDATE, DELETE, DDL, or other write operations against Sage.

The discovery tools must enforce that philosophy by construction.

---

# 3. Connection model

Use the Sage-supported System DSN model for Phase 002.

A typical setup is:

```text
Windows System DSN
       |
       v
Sage 50 Accounts v34 ODBC driver
       |
       v
Company ACCDATA directory
```

The user configures the DSN through the Windows ODBC Data Source Administrator.

LedgerLens supplies credentials when opening the connection.

Do not attempt to create or modify Windows DSNs programmatically in this phase.

Do not manipulate Sage data-directory files directly.

---

# 4. Python ODBC dependency

Add `pyodbc` as a Sage-specific optional dependency.

Do not make ODBC a mandatory dependency for running the LedgerLens web application.

Prefer an arrangement equivalent to:

```toml
[project.optional-dependencies]
sage = [
    "pyodbc>=..."
]
```

with appropriate Windows platform handling if useful.

The exact compatible version should be resolved and recorded in `uv.lock`.

The normal backend should continue to work without the Sage optional dependency installed.

The Sage discovery tooling should give a useful error if `pyodbc` is unavailable.

Do not introduce SQLAlchemy ODBC support for Sage in this phase.

Use `pyodbc` directly.

---

# 5. Sage configuration

Add optional Sage-specific settings without making them mandatory for the FastAPI application.

Use environment variables such as:

```text
LEDGERLENS_SAGE_DSN=
LEDGERLENS_SAGE_USERNAME=
LEDGERLENS_SAGE_PASSWORD=
LEDGERLENS_SAGE_QUERY_TIMEOUT_SECONDS=30
```

The password must use an appropriate secret type and must never appear in:

* logs;
* exceptions;
* reports;
* JSON discovery artifacts;
* test snapshots;
* CLI diagnostics.

The `.env.example` may contain blank placeholders but never working credentials.

The real `.env` remains ignored.

The FastAPI application must still start normally when no Sage configuration exists.

---

# 6. Package structure

Add a focused Sage discovery package approximately like:

```text
backend/src/ledgerlens/
    sage/
        __init__.py
        cli.py
        config.py
        connection.py
        diagnostics.py
        metadata.py
        capabilities.py
        profiling.py
        relationships.py
        reports.py
        models.py
```

Do not create version adapters yet.

In particular, do not create speculative classes such as:

```text
SageV34CustomerAdapter
SageV34InvoiceAdapter
```

Phase 003 and Phase 004 will decide those abstractions using Phase 002 evidence.

---

# 7. CLI

Provide a command-line discovery tool.

Use the Python standard library `argparse` unless there is a compelling reason to add another runtime dependency.

Expose a console entry point such as:

```powershell
uv run ledgerlens-sage ...
```

Useful subcommands should include approximately:

```text
ledgerlens-sage drivers
ledgerlens-sage probe
ledgerlens-sage schema
ledgerlens-sage describe-table TABLE
ledgerlens-sage capabilities
ledgerlens-sage profile
ledgerlens-sage relationships
ledgerlens-sage benchmark
ledgerlens-sage report
```

Exact naming may vary slightly if there is a clearer arrangement.

All commands must support useful `--help`.

Commands that require a Sage connection must fail clearly when configuration is absent.

---

# 8. `drivers` command

Implement:

```powershell
uv run ledgerlens-sage drivers
```

This should report locally installed ODBC drivers using `pyodbc.drivers()`.

Also report:

```text
Operating system
Python version
Python architecture
pyodbc version
```

For example:

```text
Platform:             Windows 11
Python:               3.14.3
Python architecture:  64-bit
pyodbc:               5.x

ODBC drivers:
  Sage Line 50 v34
  ...
```

Do not infer that an installed driver proves a valid company connection.

---

# 9. `probe` command

Implement a non-destructive connection diagnostic:

```powershell
uv run ledgerlens-sage probe
```

It should:

1. validate Sage configuration;
2. establish a connection;
3. confirm the connection can execute a harmless read query or metadata operation;
4. capture ODBC/driver information where available;
5. close the connection cleanly.

Report information such as:

```text
Connection:            OK
DSN:                   configured
ODBC driver name:      ...
ODBC driver version:   ...
ODBC version:          ...
DBMS/driver identity:  ...
Read access:           OK
```

Do not print:

```text
password
full connection string containing credentials
client-specific data path
```

If reporting the DSN name is considered useful locally, mark it as local/environment-specific and exclude it from sanitized committed reports.

---

# 10. Version fingerprint

Every live discovery run must capture an environment fingerprint.

Include where automatically available:

```text
LedgerLens version / Git commit
timestamp
Windows version
Python version
Python architecture
pyodbc version
ODBC driver name
ODBC driver version
ODBC API version
Sage DSN driver identity
```

Also provide fields for manually recording:

```text
Sage 50 Accounts application version
Sage 50 Accounts build number
Sage data version if displayed by Sage
```

These manual values should be supplied through command options or local metadata, not hard-coded into application code.

We need to be able to distinguish discoveries such as:

```text
Sage 50 Accounts 34.0.x
```

from:

```text
Sage 50 Accounts 34.1.x
```

later.

---

# 11. Raw discovery artifact directory

Create a local artifact convention:

```text
artifacts/
    sage/
        <version-or-fingerprint>/
            environment.json
            schema.json
            capabilities.json
            profile.json
            relationships.json
            benchmarks.json
            report.md
```

Add the raw discovery directory to `.gitignore`.

These files may describe real client/company databases and therefore must **not** automatically be committed.

Do not store raw Sage records in this directory unless a future explicit plan permits it.

Phase 002 outputs should primarily contain metadata and aggregate statistics.

---

# 12. Schema discovery

Implement:

```powershell
uv run ledgerlens-sage schema
```

Use ODBC metadata APIs where supported, including appropriate `pyodbc` cursor metadata calls.

Discover:

```text
tables
views if exposed
columns
ODBC data types
type names
column lengths
precision
scale
nullable status where reported
ordinal positions
primary-key metadata where reported
foreign-key metadata where reported
index/statistics metadata where reported
```

Do not assume the Sage driver implements all standard ODBC metadata calls correctly.

Record unsupported or incomplete capabilities rather than treating them as implementation failures.

The resulting `schema.json` must be deterministic where practical so two schema snapshots can later be compared.

Sort tables and fields consistently.

---

# 13. Do not trust declared relational metadata

One of the purposes of Phase 002 is to discover how much relational metadata Sage actually publishes through ODBC.

Do not assume:

```text
primary keys are declared
foreign keys are declared
indexes are visible
nullability metadata is accurate
```

Record:

```text
metadata says
```

separately from:

```text
observed from data
```

This distinction will matter to later version adapters.

---

# 14. `describe-table`

Implement:

```powershell
uv run ledgerlens-sage describe-table SALES_LEDGER
```

This should display schema metadata for one table without returning business records.

For example:

```text
Table: SALES_LEDGER

Column             ODBC type        Nullable    Length
------------------------------------------------------
ACCOUNT_REF        ...
NAME               ...
...
```

Do not display sample customer names, addresses, account references, emails, or other actual values by default.

Table names must be validated against the discovered metadata before being incorporated into SQL.

Never interpolate an arbitrary unchecked table name.

---

# 15. Priority Sage tables

Give particular attention to these candidate tables if present:

```text
SALES_LEDGER
SALES_CONTACT
SALES_DEL_ADDR

PURCHASE_LEDGER
PURCHASE_CONTACT
PURCHASE_DEL_ADDR

STOCK
STOCK_TRAN
PRICE_LIST

INVOICE
INVOICE_ITEM

SALES_ORDER
SOP_ITEM

PURCHASE_ORDER
POP_ITEM

AUDIT_HEADER
AUDIT_SPLIT
AUDIT_JOURNAL
AUDIT_USAGE
AUDIT_VAT

NOMINAL_LEDGER
```

This is a discovery priority list, not an assertion that all tables belong in the LedgerLens canonical model.

Record any relevant v34 tables not anticipated here.

---

# 16. SQL capability discovery

Implement a controlled capability suite.

Determine whether the Sage ODBC driver successfully supports representative read-only operations such as:

```text
simple SELECT
column projection
WHERE equality
WHERE range
ORDER BY
COUNT(*)
DISTINCT
AND / OR
parameter placeholders
single-table predicates
basic INNER JOIN
basic LEFT JOIN if supported
```

Also investigate, without assuming support:

```text
TOP
LIMIT
OFFSET
aggregate functions
date comparisons
string comparisons
case behaviour
NULL predicates
```

Do not classify an unsupported SQL feature as a defect.

Record the actual dialect behavior.

Do not attempt write statements to prove that the interface is read-only.

Sage already documents it as read-only, and LedgerLens has no reason to issue writes.

---

# 17. Parameterized queries

Determine whether normal `pyodbc` parameter markers:

```text
?
```

work reliably with representative Sage queries.

Where values are supplied, prefer bound parameters rather than embedding values into SQL text.

Table and column identifiers cannot normally be parameterized, so they must come from explicit discovered/validated identifier sets.

This safety rule should be implemented in the discovery toolkit now.

---

# 18. Fetch behaviour

Investigate efficient sequential reading.

Measure representative behavior for:

```text
fetchone()
fetchmany()
cursor iteration
```

Use bounded test sizes.

Investigate useful `arraysize` / `fetchmany` batch sizes such as:

```text
100
500
1000
5000
```

without turning Phase 002 into a microbenchmark exercise.

The goal is to establish a sensible starting point for later synchronization.

Record:

```text
rows fetched
elapsed time
approximate rows/second
batch size
table
selected column count
```

Do not retain row contents in benchmark artifacts.

---

# 19. Query timeout

Apply the configured Sage query timeout where supported.

Long-running discovery queries must not block indefinitely.

A failed timeout capability should be recorded if the driver does not support it as expected.

The CLI should provide clear progress around potentially expensive operations.

Do not run an unbounded expensive benchmark automatically merely because `profile` or `report` is invoked.

---

# 20. Table profiling

Implement a safe table profiler.

For selected priority tables, capture where practical:

```text
row count
column count
nullable-column metadata
observed null counts for selected structural fields
minimum/maximum dates for selected date fields
distinct counts for selected coded fields
```

Avoid collecting or persisting business data values.

Do not persist:

```text
customer names
supplier names
addresses
emails
telephone numbers
free-text descriptions
invoice descriptions
contact names
client-specific account references
stock codes
```

unless explicitly required by a later approved phase.

Coded/boolean distributions may be recorded where the values are generic Sage codes, for example:

```text
0 -> count
1 -> count
```

when useful to understand field semantics.

---

# 21. Relationship validation

Use Sage's published table-link guidance as hypotheses to test against real v34 data.

Where the relevant tables exist, examine relationships including:

```text
INVOICE.ACCOUNT_REF
    -> SALES_LEDGER.ACCOUNT_REF

INVOICE.INVOICE_NUMBER
    -> INVOICE_ITEM.INVOICE_NUMBER

SALES_ORDER.ACCOUNT_REF
    -> SALES_LEDGER.ACCOUNT_REF

SALES_ORDER.ORDER_NUMBER
    -> SOP_ITEM.ORDER_NUMBER

SOP_ITEM.STOCK_CODE
    -> STOCK.STOCK_CODE

PURCHASE_ORDER.ACCOUNT_REF
    -> PURCHASE_LEDGER.ACCOUNT_REF

PURCHASE_ORDER.ORDER_NUMBER
    -> POP_ITEM.ORDER_NUMBER

POP_ITEM.STOCK_CODE
    -> STOCK.STOCK_CODE

SALES_LEDGER.ACCOUNT_REF
    -> AUDIT_HEADER.ACCOUNT_REF

PURCHASE_LEDGER.ACCOUNT_REF
    -> AUDIT_HEADER.ACCOUNT_REF

NOMINAL_LEDGER.ACCOUNT_REF
    -> AUDIT_SPLIT.NOMINAL_CODE

AUDIT_HEADER.HEADER_NUMBER
    -> AUDIT_JOURNAL.HEADER_NUMBER
```

For each tested relationship, capture safe aggregate information such as:

```text
left table
left column
right table
right column

left row count
non-null relationship values
distinct key count
duplicate key behavior
matched count
unmatched/orphan count
observed cardinality
```

Do not persist the unmatched business keys themselves.

---

# 22. Cardinality matters

Do not assume relationships are conventional database foreign keys.

Determine observed patterns such as:

```text
one-to-one
one-to-many
many-to-one
potentially many-to-many
non-unique business identifier
nullable relationship
```

In particular, determine whether likely identifiers such as:

```text
ACCOUNT_REF
INVOICE_NUMBER
ORDER_NUMBER
STOCK_CODE
HEADER_NUMBER
SPLIT_NUMBER
```

are unique in the tables where LedgerLens might rely on them.

Record evidence, not assumptions.

---

# 23. Deleted/inactive/history behavior

Investigate structural flags where present, especially fields such as:

```text
DELETED_FLAG
DATE_FLAG
ACTIVE
INACTIVE
```

and other obvious Sage state/coded fields.

Do not infer semantics solely from names.

Cross-reference Sage's published coded-variable documentation where useful.

Record only generic distributions and conclusions.

This will become important when deciding whether LedgerLens synchronizes:

```text
active records only
all records
deleted-history records
archived/history records
```

---

# 24. Date and datetime behavior

Investigate how the ODBC driver returns Sage date fields.

Record:

```text
Python type returned
ODBC type
presence/absence of time component
NULL representation
earliest/latest structural date where safe
```

Test parameterized date predicates against representative date columns.

Determine whether Sage exposes placeholder/sentinel dates and record that if observed.

Do not design canonical date rules yet.

---

# 25. Numeric and monetary behavior

For representative monetary and numeric columns, record:

```text
ODBC type
Python type
precision
scale
Decimal versus float behavior
NULL behavior
```

LedgerLens should eventually preserve accounting values exactly.

If the ODBC driver returns monetary fields as floating-point values, document this explicitly for Phase 003.

Do not silently coerce financial values into binary floating point in persistent LedgerLens models.

---

# 26. Boolean and coded fields

Identify whether Sage exposes boolean-like values as:

```text
BIT
INTEGER
SMALLINT
CHAR
other coded values
```

Record this behavior for representative tables.

Do not prematurely convert all 0/1 fields into canonical booleans; some Sage numeric flags may have more than two defined values.

---

# 27. Text behavior

Investigate:

```text
Unicode handling
trailing spaces
fixed versus variable length
empty string versus NULL
case sensitivity
maximum reported lengths
```

Use metadata and safe synthetic/local inspection.

Do not persist actual client text in committed artifacts.

This will affect later:

```text
normalization
hashing
search indexing
change detection
```

---

# 28. Benchmark suite

Implement an explicitly invoked benchmark command.

For example:

```powershell
uv run ledgerlens-sage benchmark
```

It must not run automatically as part of ordinary unit tests.

Benchmark representative operations including:

```text
metadata enumeration
COUNT on selected tables
bounded sequential read
filtered lookup
ORDER BY
representative join
```

Capture:

```text
operation
table(s)
row count/fetch count
elapsed time
rows per second where meaningful
success/failure
```

Run each benchmark enough times to identify gross performance characteristics, not to produce statistically rigorous microbenchmarks.

Do not hammer a production Sage installation.

Default behavior should be conservative.

---

# 29. Single-table versus joined extraction

One especially useful Phase 002 question is whether LedgerLens should read normalized Sage tables separately and perform relationships later in PostgreSQL.

Compare, where safe:

```text
single-table sequential extraction
```

against a small representative ODBC join.

Document whether joining through Sage ODBC creates a significant performance penalty.

Do not redesign the application architecture solely from one timing result, but provide evidence for Phase 003/004.

---

# 30. No concurrency testing yet

Do not implement parallel Sage readers or concurrent ODBC extraction.

Phase 002 benchmarks should be single-process and predominantly single-connection.

We first need to understand the driver's basic behavior.

Concurrency, locking, and synchronization scheduling belong in later phases.

---

# 31. Sanitized discovery report

Provide:

```powershell
uv run ledgerlens-sage report
```

which combines discovery artifacts into a readable Markdown report.

The report should contain sections such as:

```text
Environment fingerprint
Driver capabilities
Schema overview
Priority tables
Potential identifiers
Published relationships tested
Observed cardinalities
Data-type observations
SQL capability matrix
Performance observations
Risks / unknowns
Recommendations for Phase 003
```

The report generator must have a sanitized mode suitable for committing to Git.

The sanitized report must not contain:

```text
Sage username
password
DSN credentials
client/company name
company path
customer/supplier names
addresses
emails
telephone numbers
actual account references
actual stock codes
invoice/order numbers
free-text business data
```

---

# 32. Open-source repository hygiene

Do not commit a wholesale raw dump of a Sage client's ODBC schema or data.

Raw discovery artifacts stay ignored.

Commit only:

* LedgerLens discovery code;
* tests;
* generic documentation;
* a deliberately sanitized/curated v34 discovery summary where appropriate;
* the minimum Sage table/column knowledge later required by LedgerLens code.

Avoid copying large quantities of Sage proprietary documentation verbatim into the repository.

Where Sage documentation informs a conclusion, summarize it and reference the source.

---

# 33. Documentation structure

Add approximately:

```text
docs/
    sage/
        README.md
        v34/
            discovery.md
            relationships.md
            capabilities.md
            performance.md
```

These documents should become the curated engineering record.

They should clearly distinguish:

```text
Official Sage documentation
Observed from ODBC metadata
Observed from live Sage data
LedgerLens interpretation
Unknown / requires further investigation
```

Do not blur these categories.

---

# 34. Tests

Add comprehensive unit tests that require no Sage installation.

Mock the pyodbc boundary rather than mocking large portions of business logic.

At minimum test:

## Configuration

* Sage configuration is optional for normal application startup.
* discovery commands requiring Sage fail clearly without it;
* password values are redacted;
* timeout validation works.

## Driver diagnostics

* architecture reporting;
* driver enumeration;
* missing pyodbc handling;
* no matching Sage driver handling.

## Connection

* successful connection lifecycle;
* failed authentication;
* connection failure sanitization;
* password/connection details do not leak;
* connections close correctly.

## Metadata

* table enumeration;
* deterministic table ordering;
* column extraction;
* missing PK/FK/index metadata;
* driver metadata errors handled clearly.

## Identifier safety

* valid discovered table accepted;
* unknown table rejected;
* malformed identifier rejected;
* no arbitrary table-name interpolation.

## Capability runner

* supported capability recorded;
* unsupported feature recorded rather than crashing whole discovery;
* query parameters passed separately.

## Profiling

* aggregate output only;
* no raw row values persisted;
* errors on individual tables do not corrupt the full report.

## Relationships

* matched/unmatched counts;
* duplicate-key behavior;
* cardinality classification;
* no raw business keys in artifacts.

## Reporting

* deterministic output;
* secret redaction;
* client-specific values excluded from sanitized report.

---

# 35. Live integration testing

Add a separate opt-in Sage integration marker or equivalent.

It must not run in normal CI.

For example:

```powershell
uv run pytest --run-sage-integration -m sage_integration
```

These tests may execute against a configured real Sage v34 DSN.

They must remain read-only.

At minimum verify:

```text
connection succeeds
tables can be enumerated
priority tables can be queried where present
metadata can be collected
a bounded sequential fetch succeeds
```

If a priority table is absent in the installed Sage edition, report/skip appropriately rather than assuming corruption.

---

# 36. CI

Normal GitHub Actions cannot be expected to contain Sage 50 Accounts or its proprietary ODBC driver.

Therefore:

* do not require a Sage DSN in hosted CI;
* do not add Sage credentials to GitHub secrets;
* do not attempt to install Sage itself in CI.

Update the Windows backend smoke job to install the Sage optional Python dependency if practical:

```text
uv sync --extra sage ...
```

and verify that `pyodbc` can import.

The Windows CI job should still run all Sage discovery unit tests using mocks/fakes.

Linux CI should continue to pass without needing the Sage optional dependency.

Do not make ordinary CI dependent on proprietary Sage software.

---

# 37. README

Extend the developer documentation with a short Sage discovery section.

Include:

```text
Phase 002 requires Windows for real Sage discovery.
The normal web application does not require Sage configuration.
A matching Sage 50 ODBC driver must be installed.
A System DSN must be configured for the Sage company.
```

Explain at a high level that Sage v28.1+ DSNs normally point at the company's `ACCDATA` directory.

Do not put an actual company path or credentials in the README.

Document the main commands.

---

# 38. Security and safety

All Sage access in LedgerLens remains read-only.

The implementation must not contain code paths issuing:

```text
INSERT
UPDATE
DELETE
CREATE
ALTER
DROP
TRUNCATE
```

against Sage.

Do not implement a generic "execute arbitrary SQL" CLI command.

Do not provide an unrestricted `--sql` option.

Discovery queries must be defined by LedgerLens code and use validated identifiers.

Do not log complete SQL parameter values when those values may contain business data.

---

# 39. Explicitly out of scope

Do not implement:

* canonical Customer model;
* canonical Supplier model;
* canonical Product model;
* canonical Invoice model;
* canonical CreditNote model;
* canonical Quotation model;
* canonical SalesOrder model;
* canonical PurchaseOrder model;
* canonical Transaction model;
* Sage version adapter interface;
* synchronization;
* incremental synchronization;
* change hashing;
* PostgreSQL import from Sage;
* Typesense indexing from Sage;
* global search;
* Sage background service;
* Windows service packaging;
* multi-company synchronization;
* authentication;
* authorization;
* reporting;
* dashboards;
* production deployment;
* Sage writes;
* SDO integration;
* Sage REST APIs;
* concurrent Sage extraction;
* automatic DSN creation.

Do not expand Phase 002 into Phase 003.

---

# 40. Phase 002 questions that must be answered

The final discovery report should answer as many of these as the real driver/data permits.

### Environment

1. What exact Sage 50 Accounts v34 build was tested?
2. What exact ODBC driver version was tested?
3. Is the driver 64-bit and compatible with Python 3.14/pyodbc?

### Schema

4. How many tables/views are exposed?
5. Do ODBC metadata APIs expose useful PK information?
6. Do they expose useful FK information?
7. Are indexes/statistics visible?
8. Which priority accounting tables exist?
9. Are obvious identifiers reported as nullable/unique?

### SQL behavior

10. Which basic SQL constructs work?
11. Do parameterized predicates work reliably?
12. What pagination constructs, if any, work?
13. What date comparison behavior is observed?
14. How are NULLs represented?

### Python types

15. How are dates returned?
16. How are monetary values returned?
17. How are booleans/coded flags returned?
18. How is text returned?

### Relationships

19. Do Sage's documented links hold against the tested data?
20. Which relationships have orphaned values?
21. Which keys are non-unique?
22. What cardinalities are observed?

### Performance

23. How expensive is table enumeration?
24. How expensive are row counts?
25. What sequential-fetch throughput is observed?
26. What batch size appears reasonable?
27. Are filtered lookups substantially faster than scans?
28. How expensive are joins through ODBC?
29. Does evidence favour extracting individual tables and joining later in PostgreSQL?

### Synchronization implications

30. Are there credible modification timestamps on the important tables?
31. Are there monotonic IDs or sequence-like identifiers?
32. How are deletions represented?
33. Is there enough information for incremental synchronization, or will some tables require reconciliation/scanning?

Questions 30–33 are observations only in Phase 002. Do not build synchronization from them.

---

# 41. Acceptance criteria — implementation

Before live Sage testing:

```powershell
cd backend
uv sync --extra sage
```

must succeed on Windows.

The following should succeed:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Frontend checks should remain green even though no frontend Phase 002 feature is expected.

Normal Docker/PostgreSQL/Typesense functionality must not regress.

Normal GitHub Actions must remain green without access to Sage.

---

# 42. Acceptance criteria — live Sage v34 discovery

Phase 002 is not fully complete until the toolkit has been exercised against a real Sage 50 Accounts v34 company dataset.

At minimum:

```powershell
uv run ledgerlens-sage drivers
uv run ledgerlens-sage probe
uv run ledgerlens-sage schema
uv run ledgerlens-sage capabilities
uv run ledgerlens-sage profile
uv run ledgerlens-sage relationships
uv run ledgerlens-sage benchmark
uv run ledgerlens-sage report
```

must have been evaluated as appropriate against the live DSN.

Not every command must succeed for every ODBC capability.

Unsupported driver behavior should be documented.

The important outcome is that failures are understood and represented accurately.

---

# 43. Manual Sage cross-check

For a small number of structural observations, manually compare ODBC results to the Sage desktop application.

Examples may include:

```text
customer count
invoice count or recent invoice presence
stock/product count
known customer/invoice relationship
```

Do this only as necessary to validate interpretation.

Do not copy real client data into the repository or completion report.

Record conclusions such as:

```text
Observed SALES_LEDGER records correspond to Sage customer records.
```

rather than recording the customer names themselves.

---

# 44. Completion report

Create:

```text
docs/phase-002-completion.md
```

The report should contain:

1. Summary.
2. Exact Sage application version tested.
3. Exact Sage build tested.
4. Exact ODBC driver tested.
5. Python/pyodbc environment.
6. Files created/modified.
7. Dependencies added.
8. CLI commands implemented.
9. Unit-test results.
10. Sage integration-test results.
11. Schema-discovery findings.
12. SQL capability matrix.
13. Important tables discovered.
14. Key data-type findings.
15. Relationship findings.
16. Performance findings.
17. Incremental-sync-relevant observations.
18. Known driver limitations.
19. Security/privacy checks.
20. Deviations from this plan.
21. Questions still unanswered.
22. Recommendations for Phase 003.

Do not put client-identifying information in the completion report.

---

# 45. Phase 003 handoff

Phase 002 should finish with an evidence-based recommendation for the canonical accounting model.

Do not implement that recommendation.

The expected next step is approximately:

```text
Phase 003
Canonical Accounting Domain Model
```

Phase 003 will use the Sage evidence gathered here to decide how LedgerLens represents concepts such as:

```text
Customer
Supplier
Product
Invoice
InvoiceLine
CreditNote
SalesOrder
Quotation
Transaction
NominalAccount
```

The Phase 003 model must not simply mirror Sage table names.

Phase 002 exists specifically to prevent us from designing that model blindly.

---

# 46. Implementation discipline

Prefer small, typed, testable components.

Keep `pyodbc` behind a narrow Sage-specific boundary.

Do not expose pyodbc cursor/row objects outside the ODBC/discovery layer.

Do not add abstractions without evidence that they are needed.

Do not invent Sage behavior when the real driver can answer the question.

When the ODBC driver behaves unexpectedly:

1. capture the behavior;
2. add a focused regression test where possible;
3. document the observation;
4. avoid hiding it behind a speculative workaround.

The output of this phase should be trustworthy evidence about Sage, not an attempt to make Sage look like a conventional relational database.
