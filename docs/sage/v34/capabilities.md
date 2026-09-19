# v34 SQL and driver capabilities

Live observation: Sage application/build `34.0.23.0` (reported by the user from
Help > About), driver `SDBC.DLL`, `34.0.23.0 Sage 50 Accounts ODBC Driver`, ODBC API
`03.80.0000`. These findings do not assert compatibility with another v34 build.

Representative suite against INVOICE:

| Probe | Observed result |
| --- | --- |
| SELECT *, projection, equality/range predicates | Executed |
| ORDER BY, COUNT(*), AND/OR, NULL predicates | Executed |
| MIN/MAX aggregate | Executed |
| INNER JOIN / LEFT JOIN to SALES_LEDGER | Executed |
| TOP 1 | Executed; fetched one row |
| LIMIT / OFFSET ... FETCH NEXT | Failed: 42000 |
| DISTINCT projection | Failed: 42S22 |
| `WHERE ? = ?` with integer parameters | Failed: 22018 |
| String column equality with a bound Python string | Failed: HY004 |
| Case comparison using bound Python strings | Failed: HY004; case semantics unknown |
| Date column comparison with a bound Python date | Executed |

Execution success is not a complete semantic test. Equality/range probes use
column self-comparisons; string probes use a synthetic value. Syntax/type errors
are retained as failures, not universally classified as unsupported features.
Do not conclude that all parameter markers fail: the date probe succeeded.

Metadata: SQLColumns worked for all 119 exposed tables; SQLPrimaryKeys and
SQLForeignKeys returned IM001 throughout. SQLStatistics succeeded but returned
zero records. Index visibility and physical indexing are different questions.

The driver rejects the query-timeout setter with HY092 and reports zero afterward.
The CLI process deadline is therefore essential. No timeout-triggering expensive
query was deliberately issued. Unnecessary braces around DSN and credentials
caused IM002 and 28000 respectively; validated plain attributes connected.
Braced special-character credentials have not been live-tested.

Interpretation: investigate the driver's accepted bound string/numeric types
before implementing filtered extraction. Do not work around these failures by
interpolating business values into SQL. No write statements were attempted.
