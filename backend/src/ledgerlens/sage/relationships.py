from collections import Counter
from dataclasses import asdict
from typing import cast

from ledgerlens.sage.config import SageError
from ledgerlens.sage.connection import Connection, ReadError, read
from ledgerlens.sage.metadata import column_named, failure, table_named
from ledgerlens.sage.models import LINKS, Json, Observation, Schema


def summarize(left: list[object], right: list[object], *, complete: bool) -> dict[str, Json]:
    # Keys stay in memory only. Exact Python equality; driver collation may differ.
    lcounts = Counter(value for value in left if value is not None)
    rcounts = Counter(value for value in right if value is not None)
    overlap = lcounts.keys() & rcounts.keys()
    matched = sum(lcounts[key] for key in overlap)
    left_many = any(lcounts[key] > 1 for key in overlap)
    right_many = any(rcounts[key] > 1 for key in overlap)
    cardinality = (
        "no-matches"
        if not overlap
        else "potentially-many-to-many"
        if left_many and right_many
        else "many-to-one"
        if left_many
        else "one-to-many"
        if right_many
        else "one-to-one"
    )
    return {
        "left_rows_fetched": len(left),
        "right_rows_fetched": len(right),
        "left_nonnull": sum(lcounts.values()),
        "right_nonnull": sum(rcounts.values()),
        "left_distinct": len(lcounts),
        "right_distinct": len(rcounts),
        "left_duplicate_excess": sum(lcounts.values()) - len(lcounts),
        "right_duplicate_excess": sum(rcounts.values()) - len(rcounts),
        "matched_left_rows": matched,
        "unmatched_left_rows_in_sample": sum(lcounts.values()) - matched,
        "orphan_count": sum(lcounts.values()) - matched if complete else None,
        "observed_cardinality": cardinality,
        "both_reads_complete": complete,
        "scope": "full bounded reads" if complete else "sample overlap only; no orphan conclusion",
        "comparison": "Python equality; Sage collation and audit account-type semantics unverified",
    }


def relationships(connection: Connection, schema: Schema, limit: int = 100) -> list[Observation]:
    results = []
    for link in LINKS:
        details = cast(dict[str, Json], asdict(link))
        name = f"{link.left_table}.{link.left_column}->{link.right_table}.{link.right_column}"
        try:
            left = table_named(schema, link.left_table)
            right = table_named(schema, link.right_table)
            lc = column_named(left, link.left_column)
            rc = column_named(right, link.right_column)
        except SageError:
            results.append(Observation(name, "not-tested", details=details))
            continue
        try:
            lrows = read(connection, f"SELECT {lc} FROM {left.name}", limit=limit + 1)
            rrows = read(connection, f"SELECT {rc} FROM {right.name}", limit=limit + 1)
            details.update(
                summarize(
                    [row[0] for row in lrows[:limit]],
                    [row[0] for row in rrows[:limit]],
                    complete=len(lrows) <= limit and len(rrows) <= limit,
                )
            )
            results.append(Observation(name, "supported", details=details))
        except ReadError as error:
            observation = failure(name, error)
            observation.details = details
            results.append(observation)
    return results
