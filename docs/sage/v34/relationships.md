# v34 relationship observations

**Official guidance:** [Sage's table-link article](https://gb-kb.sage.com/portal/app/portlets/results/viewsolution.jsp?solutionid=200427112158420)
supplies hypotheses, including account-reference links and document-to-line
links. It does not promise that ODBC publishes foreign-key constraints.

**Live observations, 34.0.23.0:** all twelve links listed in the Phase 002 plan
had the necessary tables/columns and were read successfully. Each side was
limited to 100 rows plus a completeness lookahead. Neither side of any tested
pair was fully covered, so **no global orphan count or uniqueness claim is made**.

Matched subsets of invoice/line, sales-order/line, purchase-order/line, nominal/
audit-split, and audit-header/journal pairs showed one-to-many patterns. Other
samples had very small or zero overlap. Different unordered table prefixes can
miss valid counterparts; zero overlap is not evidence of a broken relationship.
The apparent one-to-one patterns in small matched subsets are not domain rules.

Duplicate non-null identifiers occurred on some line/account-reference sides.
The artifacts contain aggregate duplicate/match counts, never actual keys.
Matching uses exact Python equality. Driver collation, blank/padded keys, service
items, account-type distinctions in AUDIT_HEADER, and deleted/history records
need targeted semantic investigation before treating these links as foreign keys.

**Interpretation:** document-to-line structures are credible starting hypotheses
for Phase 003, while stable document keys, account scopes, and orphan handling
remain undecided. Wider or targeted validation is necessary before synchronization.
