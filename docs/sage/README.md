# Sage ODBC discovery

This is a standalone, read-only engineering toolkit, not synchronization. The
FastAPI application does not import pyodbc or require Sage settings.

## Setup

Use Windows 11, 64-bit Python 3.14, and the matching Sage v34 64-bit ODBC driver.
Create a **System DSN** in the 64-bit Windows ODBC administrator. Point it at the
company's `ACCDATA` directory for v28.1+. Do not edit company files or create a DSN
through LedgerLens. This follows [Sage's 64-bit connection guidance](https://gb-kb.sage.com/portal/app/portlets/results/viewsolution.jsp?solutionid=230619135150357).

From `backend/`, `uv sync --locked --extra sage` installs the Windows-only optional
pyodbc dependency. Linux and the normal web application need no ODBC installation.
In the ignored root `.env`, configure `LEDGERLENS_SAGE_DSN`,
`LEDGERLENS_SAGE_USERNAME`, `LEDGERLENS_SAGE_PASSWORD`, and optionally
`LEDGERLENS_SAGE_QUERY_TIMEOUT_SECONDS` (1–300, default 30). A blank password is
allowed when the Sage account uses one. Never pass credentials on the command line.

## Commands

Run all commands from `backend/` using `uv run --extra sage ledgerlens-sage`:

| Subcommand | Work performed |
| --- | --- |
| `drivers` | Platform/Python/architecture/pyodbc and installed drivers; no connection |
| `probe` | Read-only connection, metadata read, driver fingerprint |
| `schema` | All table/view and column metadata; PK/FK/index availability |
| `describe-table SALES_LEDGER` | One table's metadata, no business rows |
| `capabilities --table INVOICE` | Code-defined bounded SQL probes |
| `profile` | Counts and up to 100 sampled rows per priority table, aggregates only |
| `relationships` | Up to 100 keys per side of each published-link hypothesis |
| `benchmark --table INVOICE` | Two sequential repetitions, at most 100 rows per read |
| `report --sanitized` | Allowlisted Markdown summary from existing artifacts; no Sage connection |

For connected commands, repeat the same `--sage-version`, `--sage-build`, optional
`--sage-data-version`, and `--output ../artifacts/sage/local-v34` options. These
manual version fields must come from Sage's Help > About; they are not inferred
from the ODBC version. The full tested Help > About identifier was `34.0.23.0`.

Example for an explicit, conservative benchmark:

```powershell
uv run --extra sage ledgerlens-sage benchmark --table INVOICE --limit 100 --repeats 2 --sage-version 34.0.23.0 --sage-build 34.0.23.0 --output ../artifacts/sage/local-v34
uv run --extra sage ledgerlens-sage report --output ../artifacts/sage/local-v34 --sanitized
```

Without `--output`, connected commands use an opaque environment-fingerprint
directory under root `artifacts/sage/`. Reports require the directory explicitly.
An output directory cannot be reused with a different DSN/driver/manual version
fingerprint. A DSN could be repointed externally without changing its name: use a
fresh directory after any DSN/company change. Artifacts from separately invoked
commands are separate observations, not a transactionally consistent snapshot.

## Bounds, timeouts, and evidence

`--limit` is 1–10,000 sampled rows (100 by default); a one-row lookahead detects
incomplete reads. Profiles project at most 32 columns, prioritizing candidate
identifiers, flags, and record timestamps. No raw rows, keys, amounts, or text are
written. Structural date bounds and aggregate counts stay in ignored artifacts.
Numeric column `size` represents reported precision; for character columns it is
reported length. `scale` is recorded independently. Metadata is not proof of
uniqueness or accurate nullability.

Client fetch bounds do **not** bound the driver's scan/sort work. Counts, sorting,
wide projections, and joins can be expensive. Benchmark batch settings are 100,
500, 1000, and 5000; a row limit smaller than a batch cannot establish the best
batch size. No concurrent readers, full extraction, or automatic benchmarks exist.

The connection requests read-only access and login/query timeouts. This tested
driver rejects the query-timeout setter with `HY092`; CLI connected commands run
in one child process with a default **300-second whole-command deadline**. Override
with `--deadline-seconds` when appropriate. The child is terminated on expiry;
partial artifacts do not establish acceptance. Profile results are saved after
each completed table. Other suites write their result on completion; a killed
run may leave only earlier artifacts. Use fresh directories to avoid confusing
old results with an interrupted rerun. Live pytest checks have their own 60-second
worker deadline per check. Direct Python API callers must supply their own deadline
when the driver cannot enforce a query timeout.

Missing metadata/features are recorded. `IM001`, `HYC00`, and `0A...` indicate an
unsupported operation. Other SQLSTATEs are recorded as failures for investigation,
not reclassified as unsupported merely because a query failed. Driver messages,
connection strings, and parameter values are never emitted. The tested driver
misparses unnecessary attribute braces; delimiter-free values are passed plainly,
while values needing protection retain ODBC escaping. Special-character credentials
requiring braces need separate live verification; no unsafe fallback is attempted.

## Reporting and privacy

The six JSON artifacts are `environment`, `schema`, `capabilities`, `profile`,
`relationships`, and `benchmarks`; `report.md` combines them. All stay ignored.
Each newly written artifact has a small `.provenance.json` sidecar recording the
command timestamp, run ID, environment fingerprint, selected tables and configured
limits where applicable. Completion marks distinguish in-progress, partial, and
complete commands; complete means the command finished, not that every query
succeeded. Report provenance retains the source sidecars. Older artifacts without
sidecars remain readable and are explicitly shown as having unknown provenance.
Count and bounded-sample outcomes are reported independently, including safe
failure SQLSTATEs and the number of sampled rows.
`--sanitized` is the default and omits arbitrary strings, the full schema, DSN,
credentials, company paths, business keys, and free text. `--local-detail` is an
explicit local metadata/aggregate report, not a report to commit. Only curated
engineering conclusions belong in `docs/sage/v34/`. Review them before sharing.
The two report-mode flags are mutually exclusive. Sanitization preserves structural
metadata and omits potentially sensitive text values; it never replaces credential
substrings inside field names, versions, table/column names, or generated identifiers.

The Git commit is a separate environment field, not an input to the fingerprint.
The fingerprint uses the DSN, pyodbc version, driver version, and supplied Sage
version/build/data-version fields. Uncommitted discovery code may be newer than
the recorded commit. Record the worktree status in the completion report.

## Tests and evidence categories

`uv run pytest` uses fakes at the pyodbc boundary and needs no Sage installation.
`uv run --extra sage pytest --run-sage-integration -m sage_integration` explicitly
connects to the local company. Hosted Linux CI omits pyodbc; Windows CI installs
the extra, verifies import via `drivers`, and runs the fake-based tests only.

- **Official documentation:** DSN setup, table-link and coded-variable hypotheses.
- **ODBC metadata:** driver declarations, independently recorded.
- **Live observations:** exact tested build and bounded/aggregate query results.
- **Interpretation:** provisional engineering recommendations, not domain rules.
- **Unknowns:** explicitly listed in the curated findings and completion report.

See [discovery](v34/discovery.md), [capabilities](v34/capabilities.md),
[relationships](v34/relationships.md), and [performance](v34/performance.md).
