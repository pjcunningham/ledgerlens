# Phase 002 completion report

Date: 2026-09-19. Implementation and live discovery acceptance were exercised
locally. Driver errors and unanswered semantic questions are recorded below;
they are not hidden or counted as successful SQL features. Hosted CI has not
been run for these uncommitted changes. No commit or push was performed.

## 1. Summary

Added a separate, read-only Sage discovery CLI with optional pyodbc, validated
DSN configuration, driver/environment diagnostics, schema discovery, controlled
SQL probes, bounded aggregate profiling, published-link sampling, sequential
benchmarks, and sanitized Markdown reporting. No canonical models, adapters,
synchronization, PostgreSQL imports, Typesense indexing, or frontend features
were added. Live Sage access was available after the user configured the ignored
root `.env`, so the requested work proceeded beyond offline implementation.

## 2–5. Exact environment

| Item | Tested environment |
| --- | --- |
| Sage application version | 34.0.23.0, supplied by user from Help > About |
| Sage build | Same full Help > About identifier, 34.0.23.0; no separate build field supplied |
| Sage data version | Not separately supplied; unknown |
| ODBC driver | SDBC.DLL; 34.0.23.0 Sage 50 Accounts ODBC Driver |
| ODBC API / DBMS identity | 03.80.0000 / Sterling |
| Operating system | Windows 11, build 26200 |
| Python | 3.14.3, 64-bit |
| pyodbc | 5.3.0 |
| LedgerLens | 0.1.0; working tree based on a10eab0e8b452da29fa34833b1bd222b3fff663f |

The discovery implementation is uncommitted and therefore newer than the base
commit in the separate environment field (not part of the fingerprint calculation).
Raw local artifacts remain ignored, and no DSN name,
username, password, company path, business keys, or records are included here.

## 6. Files created or modified

- `backend/src/ledgerlens/sage/`: `__init__.py`, `config.py`, `connection.py`,
  `models.py`, `diagnostics.py`, `metadata.py`, `capabilities.py`, `profiling.py`,
  `relationships.py`, `benchmarks.py`, `reports.py`, `cli.py`.
- `backend/tests/sage/`: fake pyodbc boundary and offline regression tests;
  `backend/tests/test_sage_integration.py`; integration gating in `tests/conftest.py`.
- `backend/pyproject.toml`, `backend/uv.lock`: optional dependency, CLI entry point,
  and test marker.
- `.env.example`, `.gitignore`, `.github/workflows/ci.yml`, `README.md`.
- `docs/sage/README.md`, the four curated `docs/sage/v34/` records, and this report.

Temporary diagnostic scripts were used for metadata field names, safe local
configuration checks, and validation; they are removed before handoff. The user's
pre-existing staged/unstaged Phase 002 plan is preserved without edits.

## 7. Dependencies added

Only `pyodbc>=5.3,<6; sys_platform == 'win32'`, resolved to **5.3.0** in uv.lock,
under the optional `sage` extra. It has Python 3.14 Windows wheels. The CLI uses
argparse; no CLI framework, ODBC ORM, retry framework, or service dependency was
added. pyodbc loads only at the Sage boundary and is unnecessary for FastAPI.

## 8. CLI and architectural decisions

Implemented `drivers`, `probe`, `schema`, `describe-table`, `capabilities`,
`profile`, `relationships`, `benchmark`, and `report`, each with help.

Identifiers must be safe and present in discovered metadata; values use bound
parameters. Queries are code-defined SELECTs. There is no arbitrary SQL option.
Connections request read-only access and close explicitly. Driver failures expose
only safe diagnostics/SQLSTATEs, never driver messages or parameter values.

Dataclasses record metadata and observations. Raw rows remain inside the discovery
layer and are discarded after aggregation. Metadata declarations are separate
from sampled evidence. Deterministic schema ordering and an allowlisted sanitized
report support comparison and curated documentation. Output stays inside ignored
`artifacts/sage/`. No app API exposes Sage metadata or business data.

The driver rejects its query timeout setting. One CLI child process owns the
connection, and the parent enforces a whole-command deadline (default 300 seconds).
This is a watchdog, not concurrent extraction. Live pytest checks have an
independent 60-second worker deadline. Direct Python API callers must provide
their own deadline when the driver cannot enforce a query timeout.

## 9. Offline automated checks

All required non-Sage local checks passed. Final verification results:

| Check | Result |
| --- | --- |
| Optional Sage install | PASS; pyodbc 5.3.0 installed on 64-bit Python 3.14.3 |
| `uv run ruff check .` | PASS; all checks passed |
| `uv run ruff format --check .` | PASS; 35 files already formatted |
| `uv run mypy src` | PASS; 25 source files |
| `uv run pytest` | PASS after review fixes; 134 passed, 23 intentionally skipped, 50 warnings |
| Targeted review regressions | PASS; 9 passed before the full suite |
| `uv run uv lock --check` | PASS; 49 packages resolved, lockfile current |
| Frontend lint / format / typecheck | PASS |
| Frontend tests | PASS; 15 tests in 2 files |
| Frontend build | PASS; 3,333 modules; existing large-chunk advisory |
| Compose config / existing services | PASS; PostgreSQL and Typesense healthy |
| Infrastructure pytest | PASS; 1 passed, 145 deselected |
| Alembic upgrade / check | PASS; no new upgrade operations |
| Python sdist/wheel build | PASS via `uv run uv build` |
| YAML / artifact and credential hygiene | PASS; workflow parsed, System DSN confirmed, no configured Sage credential values in tracked/unignored files or local JSON |
| `git diff --check` | PASS |

Added 75 offline Sage tests. They cover optional configuration, redaction,
missing pyodbc/drivers, architecture,
connection cleanup/authentication failures, real-driver attribute-brace and timeout
regressions, metadata ordering/unsupported APIs/legacy names, identifier safety,
parameter binding, bounded fetch modes, aggregates, partial relationship scope,
cardinality, reports, all CLI help commands, output paths, and the process deadline.
Existing Starlette/AnyIO/Typesense deprecation warnings remain visible.

Review fixes preserve structural metadata during sanitization, including short
credential overlaps with dictionary keys and fingerprints. Potentially sensitive
text values are omitted by field rather than replacing credential substrings.
Count and sample observations are independent; regression tests exercise all four
success/failure combinations and verify safe SQLSTATE and sample-size reporting.
Report modes are mutually exclusive. Small per-artifact provenance sidecars retain
command time, run ID, selected tables, configured bounds, and completion status;
the report records its sources and labels missing legacy provenance explicitly.
The Git commit remains a separate environment field, outside the fingerprint.

## 10. Live Sage acceptance

All required command families were evaluated against the configured company:
drivers, probe, schema, capabilities (INVOICE), profile (19 present priority
tables), relationships (12 hypotheses), benchmark (INVOICE, two repeats, 100-row
limit), and sanitized report. Describe-table also executed successfully against
SALES_LEDGER. Per-operation failures remain in ignored artifacts.

`uv run pytest --run-sage-integration -m sage_integration`: **20 passed,
2 skipped**, 125 deselected, 36.49 seconds in the deadline-protected run.
The skips are absent SALES_CONTACT and
PURCHASE_CONTACT tables, not failed assumptions about the installed edition.
Tests verified the connection, metadata, and bounded reads of present priority tables.
The user confirmed that customer/product totals match the Sage desktop application.

After the review fixes, `profile` and `report --sanitized` were rerun against the
same configured v34 DSN. All 19 present priority tables produced successful count
and bounded-sample observations independently, with at most 100 sampled rows per
table. The profile sidecar records completion and the report retains its source
provenance; earlier capability/relationship/benchmark artifacts are explicitly
identified as legacy observations without sidecars. Local privacy checks passed:
no configured DSN, username, password, or sampled date bounds appear in the
sanitized report; profiling contains only the expected aggregate fields, with no
raw records. The full live integration suite above was not repeated for these
review fixes. No additional driver or domain findings were inferred from this rerun.

## 11–14. Schema, capabilities, tables, and types

Schema discovery found **119 tables, 3,198 columns**, no reported views. All priority
tables except SALES_CONTACT and PURCHASE_CONTACT exist. PK/FK metadata returns
IM001; index calls succeed with no rows. Legacy ODBC 2 column metadata names are
handled explicitly; missing ordinals remain unknown. No full schema is committed.

| Representative INVOICE SQL feature | Observed result |
| --- | --- |
| SELECT, projection, equality/range, AND/OR, NULL | Executed |
| ORDER BY, COUNT, MIN/MAX | Executed |
| INNER JOIN, LEFT JOIN, TOP 1 | Executed |
| Date parameter predicate | Executed |
| DISTINCT | Failed 42S22 |
| Integer `? = ?` predicate | Failed 22018 |
| String parameter / case comparison | Failed HY004 |
| LIMIT / OFFSET FETCH | Failed 42000 |

Key type finding: SALES_LEDGER.BALANCE is DOUBLE/precision 15/scale 2/buffer length
8, returned as Python **float**, not Decimal. Text returns strings; date and
timestamp columns produce date/datetime; NULL produces None; sampled flags are
integers. A raw TINYINT type code of 65530 is retained as supplied. STOCK modification
timestamps included NULL despite non-nullable metadata. These are evidence for
careful canonical rules, not a schema to copy directly.

## 15–17. Relationships, performance, and change observations

All twelve planned links were queried. Every pair used incomplete samples, so no
global orphan count or key-uniqueness claim is made. Matched document/line subsets
showed one-to-many structure. Exact Python equality does not establish Sage's
collation semantics. Audit account-type scope and deleted/service/history cases
need more targeted evidence. No actual relationship keys were retained.

Dedicated sequential benchmarks: table enumeration 0.003–0.006 seconds; COUNT
0.31–0.53; projected 100-row reads 0.54–1.15; ORDER BY 12.14–14.60; representative
join 0.80–1.08. String filtered lookups failed HY004. Larger configured batch sizes
were clipped by the 100-row limit, so no optimal batch size is claimed.

RECORD_CREATE_DATE, RECORD_MODIFY_DATE, and RECORD_DELETED appear on profiled tables.
They are candidates only: NULL coverage, update guarantees, monotonic IDs, deletion
visibility, timestamp precision/time zones, and reconciliation requirements remain
unproven. No incremental synchronization is implemented.

## 18. Known driver limitations

Unnecessary connection-attribute braces are parsed literally (IM002/28000);
safe delimiter-free values now omit them, while protected values retain escaping.
Special-character credentials still require live verification. Query timeout is
rejected (HY092), PK/FK metadata is unsupported, indexes are invisible, ordinal
metadata is absent, and several SQL/binding probes fail as listed above. No unsafe
value interpolation or speculative driver workaround was added.

## 19. Security and privacy

No Sage write statement, arbitrary SQL CLI, DSN mutation, or direct company-file
access exists. Secrets are SecretStr values; settings and driver exceptions are
redacted/sanitized. Artifacts contain metadata and aggregates only, with raw keys
and records discarded. Sanitized reporting permits only known structural labels,
safe numeric version identifiers, statuses, and aggregates. Real artifacts and
the root `.env` stay ignored; only curated findings are part of the working diff.

## 20. Deviations and limits

- Added `benchmarks.py` to keep profiling focused; used a CLI watchdog because
  this real driver rejects query-timeout configuration.
- The Sage dependency is Windows-only; Linux CI exercises fakes without ODBC.
- An early capability probe briefly overlapped a profile process due to a yielded
  command session. The profile process was stopped, rerun sequentially, and no
  concurrency test was conducted. Initial timings are not a controlled benchmark;
  the dedicated benchmark is sequential.
- Profile column selection was refined to include record timestamps; live
  profiling was repeated after that change. Legacy ODBC 2 metadata field handling
  was added after direct metadata inspection and schema discovery repeated.
- Hosted GitHub Actions cannot be verified without a push; no hosted success is claimed.
- No broad claims are made from bounded samples or from execution success alone.

## 21. Questions still unanswered

Separate data-version identifier; complete uniqueness and orphan/cardinality
coverage; reliable bound string/numeric types; DISTINCT dialect behavior; text
case/collation/normalization; sentinel-date meaning; exact money conversion;
timezone/timestamp guarantees; deletion/history semantics; trustworthy incremental
cursors and reconciliation scope; larger batch throughput and representative joins.
These questions are recorded, not answered by assumption. Wider targeted live
tests should address them before synchronization decisions.

## 22. Phase 003 handoff

Use the [curated discovery record](sage/v34/discovery.md) and linked capability,
relationship, and performance notes to design accounting concepts, not raw Sage
table replicas. Decide canonical identifiers only after scope/uniqueness checks;
use an explicit decimal accounting policy; treat nullability and change fields
as untrusted evidence until validated. Separate-table extraction remains a
hypothesis, not a conclusion forced by this small join benchmark. No Phase 003
models or version adapters have been implemented.
