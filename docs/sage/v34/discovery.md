# v34 discovery record

Date: 2026-09-19. This is a curated engineering summary, not a client schema dump.

## Evidence and environment

- User-reported Sage Help > About application/build identifier: **34.0.23.0**.
- Live driver: **SDBC.DLL**, `34.0.23.0 Sage 50 Accounts ODBC Driver`.
- Driver-reported DBMS identity: Sterling; ODBC API `03.80.0000`.
- Windows 11 build 26200; Python **3.14.3**, 64-bit; pyodbc **5.3.0**.
- The application data-version field was not separately provided; it remains unknown.

**Official guidance:** Sage's [System DSN instructions](https://gb-kb.sage.com/portal/app/portlets/results/viewsolution.jsp?solutionid=230619135150357),
[table links](https://gb-kb.sage.com/portal/app/portlets/results/viewsolution.jsp?solutionid=200427112158420),
and [coded-variable reference](https://gb-kb.sage.com/portal/app/portlets/results/viewsolution.jsp?solutionid=200427112158435)
informed setup and test hypotheses. These generic documents do not establish the
schema of every v34 release or the semantics of every field in this dataset.

## ODBC metadata observations

119 tables and 3,198 columns were exposed; no rows classified as views were returned.
All 21 priority candidates except SALES_CONTACT and PURCHASE_CONTACT were present.
Other tables exist but have not been selected as canonical concepts or copied
wholesale into the repository.

SQLColumns returns **legacy ODBC 2 metadata names** (`precision`, `length`, `scale`),
rather than `column_size`, `buffer_length`, `decimal_digits`. Discovery supports
both forms. Ordinal positions are not supplied; columns therefore sort by name.
The recorded size, numeric precision, scale, and buffer length remain distinct.
PK/FK APIs return IM001. Index/statistics calls return no records.

An unusual raw ODBC type code **65530** is reported with type name TINYINT.
It is retained as reported rather than silently normalized to signed -6.
Nullability declarations are not reliable enough for canonical constraints.

## Live data-type and identifier observations

- `SALES_LEDGER.BALANCE`: DOUBLE, reported precision 15, scale 2, buffer length 8;
  returned as Python **float**, not Decimal. Canonical monetary conversion and
  rounding require a deliberate exact-decimal policy; none is implemented here.
- ACCOUNT_REF / STOCK_CODE samples return Python strings. VARCHAR length is
  available through the legacy precision field (ACCOUNT_REF reports length 8).
  Text inspection records only length/space/Unicode/null aggregates, never values.
- Date fields return `date`; record creation/modification fields return `datetime`
  with non-midnight times. NULLs return `None`. Placeholder-date classification
  remains a heuristic and needs field-specific verification.
- DELETED_FLAG and RECORD_DELETED samples return integers, not canonical booleans.
  Only generic 0/1/2 distributions are retained. An all-active sample does not
  establish how deleted/history records behave globally.
- The first 100 SALES_LEDGER account references, STOCK codes, and INVOICE numbers
  were distinct within their respective samples. That does not establish global
  uniqueness, monotonicity, stability, or cross-company scope.
- STOCK.RECORD_MODIFY_DATE returned NULL in part of the sample even though its
  metadata reported non-nullable. This is a concrete metadata/data discrepancy.

## Modification and deletion candidates

RECORD_CREATE_DATE, RECORD_MODIFY_DATE, and RECORD_DELETED occur on the profiled
priority tables. They are credible fields to investigate, not evidence of a safe
incremental cursor. Timestamp coverage, update behavior, resolution, ordering,
NULL handling, hard deletion visibility, and history retention remain unproven.
No synchronization, hashes, or reconciliation jobs have been implemented.

## Manual cross-check

The user confirmed that the ODBC SALES_LEDGER and STOCK totals agree with Sage's
customer and product totals with filters cleared. Only that conclusion is kept
here; company-specific totals and record identities are excluded.

## Phase 003 interpretation

Use accounting concepts rather than mirroring these tables. Document/line
relationships are plausible, but identifier scope and complete cardinalities
still need evidence. Preserve decimal accounting values deliberately; do not
promote driver floats or non-nullable declarations directly into domain rules.
The [capability](capabilities.md), [relationship](relationships.md), and
[performance](performance.md) records identify the remaining questions.
