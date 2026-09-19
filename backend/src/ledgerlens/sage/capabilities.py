import sys
from dataclasses import dataclass, field
from datetime import date
from time import perf_counter

from ledgerlens.sage.config import SageError
from ledgerlens.sage.connection import Connection, ReadError, read
from ledgerlens.sage.metadata import column_named, failure, identifier, table_named
from ledgerlens.sage.models import LINKS, Observation, Schema, Table


@dataclass(frozen=True)
class Query:
    name: str
    sql: str
    parameters: tuple[object, ...] = field(default=(), repr=False)


def queries(table: Table, schema: Schema) -> list[Query]:
    t = identifier(table.name)
    c = column_named(table, table.columns[0].name)
    prefix = f"SELECT {c} FROM {t}"
    result = [
        Query("simple_select", f"SELECT * FROM {t}"),
        Query("projection", prefix),
        Query("where_equality", prefix + f" WHERE {c} = {c}"),
        Query("where_range", prefix + f" WHERE {c} >= {c}"),
        Query("order_by", prefix + f" ORDER BY {c}"),
        Query("count", f"SELECT COUNT(*) FROM {t}"),
        Query("distinct", f"SELECT DISTINCT {c} FROM {t}"),
        Query("and_or", prefix + f" WHERE ({c} IS NULL OR {c} IS NOT NULL) AND 1 = 1"),
        Query("parameters", prefix + " WHERE ? = ?", (1, 1)),
        Query("null_predicate", prefix + f" WHERE {c} IS NULL"),
        Query("top", f"SELECT TOP 1 {c} FROM {t}"),
        Query("limit", prefix + " LIMIT 1"),
        Query("offset", prefix + f" ORDER BY {c} OFFSET 1 ROWS FETCH NEXT 1 ROWS ONLY"),
    ]
    for column in table.columns:
        name = column_named(table, column.name)
        if column.odbc_type in {91, 93, 9, 11} and not any(
            q.name == "date_parameters" for q in result
        ):
            result.append(
                Query(
                    "date_parameters",
                    f"SELECT {name} FROM {t} WHERE {name} >= ?",
                    (date(2000, 1, 1),),
                )
            )
        if column.odbc_type in {1, 12, -1, -8, -9, -10} and not any(
            q.name == "string_parameters" for q in result
        ):
            result.append(
                Query(
                    "string_parameters",
                    f"SELECT {name} FROM {t} WHERE {name} = ?",
                    ("LedgerLensSyntheticProbe",),
                )
            )
            result.append(
                Query(
                    "case_comparison",
                    f"SELECT COUNT(*) FROM {t} WHERE ? = ?",
                    ("LedgerLens", "ledgerlens"),
                )
            )
        if column.odbc_type in {2, 3, 4, 5, 6, 7, 8, -5} and not any(
            q.name == "aggregate" for q in result
        ):
            result.append(Query("aggregate", f"SELECT MIN({name}), MAX({name}) FROM {t}"))
    for link in LINKS:
        if link.left_table != t:
            continue
        try:
            other = table_named(schema, link.right_table)
            left = column_named(table, link.left_column)
            right = column_named(other, link.right_column)
        except SageError:
            continue
        for kind in ("INNER", "LEFT"):
            result.append(
                Query(
                    f"{kind.lower()}_join",
                    f"SELECT L.{left} FROM {t} L {kind} JOIN {other.name} R "
                    f"ON L.{left} = R.{right}",
                )
            )
        break
    return result


def evaluate(
    connection: Connection,
    query: Query,
    *,
    limit: int = 100,
    batch: int = 100,
    method: str = "fetchmany",
) -> Observation:
    print(f"Read operation: {query.name}", file=sys.stderr)
    start = perf_counter()
    try:
        rows = read(
            connection, query.sql, query.parameters, limit=limit, batch=batch, method=method
        )
        elapsed = perf_counter() - start
        return Observation(
            query.name,
            "supported",
            details={
                "fetched_count": len(rows),
                "elapsed_seconds": elapsed,
                "rows_per_second": (
                    len(rows) / elapsed
                    if elapsed and query.name not in {"count", "aggregate", "case_comparison"}
                    else None
                ),
                "batch_size": batch,
                "fetch_method": method,
                "interpretation": "execution succeeded; results not proof of semantic correctness",
            },
        )
    except ReadError as error:
        observation = failure(query.name, error)
        observation.details["elapsed_seconds"] = perf_counter() - start
        return observation


def capabilities(connection: Connection, table: Table, schema: Schema) -> list[Observation]:
    if not table.columns:
        return [Observation("capabilities", "not-tested", details={"reason": "no column metadata"})]
    results = [evaluate(connection, query, limit=10) for query in queries(table, schema)]
    for name in (
        "date_parameters",
        "string_parameters",
        "case_comparison",
        "aggregate",
        "inner_join",
        "left_join",
    ):
        if name not in {result.operation for result in results}:
            results.append(
                Observation(name, "not-tested", details={"reason": "required metadata absent"})
            )
    return results
