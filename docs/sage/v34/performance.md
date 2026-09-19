# v34 read performance

Live observations on the configured local company with driver 34.0.23.0. These
are conservative engineering samples, not rigorous benchmarks or capacity limits.
No company name, path, records, keys, or exact business volumes are included.

Two explicit INVOICE benchmark repetitions, at most 100 fetched rows per read:

| Operation | Observed elapsed range |
| --- | --- |
| Table metadata enumeration (119 tables) | 0.003–0.006 seconds |
| COUNT(*) | 0.31–0.53 seconds |
| Single-column sequential read | 0.54–1.15 seconds |
| ORDER BY | 12.14–14.60 seconds |
| Representative INNER JOIN | 0.80–1.08 seconds |
| Bound string filtered lookup | Failed with HY004; no useful timing comparison |

Sequential throughput was approximately 87–185 fetched rows/second, including
execution and cursor cleanup. fetchone, cursor iteration, and fetchmany all worked.
Arraysize/batch configurations 100, 500, 1000, 5000 were exercised; the 100-row
limit means larger fetchmany requests were clipped, so this does not identify an
optimal large batch. Use 100 conservatively until representative larger tests.

An earlier capability probe fetched ten rows using SELECT * in about 29 seconds,
versus about 0.58 seconds with one projected column. It briefly overlapped an
accidentally started profile command, which was immediately stopped; those initial
timings are qualitative only. The dedicated two-repeat benchmark was sequential.
Prefer narrow projections. Client fetch bounds do not eliminate server scan/sort work.

**Interpretation:** this small join was not dramatically slower than the narrow
single-table read. There is insufficient evidence to favor a new architecture
on join timing alone. Separate-table extraction and later PostgreSQL joins remain
a reasonable hypothesis to evaluate, not an implemented design. Avoid ORDER BY
and broad projections unless their measured benefit justifies their cost.
