from time import perf_counter

from ledgerlens.sage.capabilities import Query, evaluate, queries
from ledgerlens.sage.connection import Connection, ReadError, read
from ledgerlens.sage.metadata import column_named, failure, metadata_rows
from ledgerlens.sage.models import Observation, Schema, Table


def benchmark(
    connection: Connection, table: Table, schema: Schema, limit: int = 100, repeats: int = 2
) -> list[Observation]:
    if not table.columns:
        return [Observation("benchmark", "not-tested")]
    results = []
    for repeat in range(repeats):
        start = perf_counter()
        try:
            rows = metadata_rows(connection, "tables")
            results.append(
                Observation(
                    "metadata_enumeration",
                    "supported",
                    details={
                        "elapsed_seconds": perf_counter() - start,
                        "fetched_count": len(rows),
                    },
                )
            )
        except ReadError as error:
            results.append(failure("metadata_enumeration", error))
        available = queries(table, schema)
        for query in available:
            if query.name in {"count", "order_by", "inner_join"}:
                results.append(evaluate(connection, query, limit=limit))
        c = column_named(table, table.columns[0].name)
        query = Query("sequential_read", f"SELECT {c} FROM {table.name}")
        for method in ("fetchone", "iteration", "fetchmany"):
            for batch in (100, 500, 1000, 5000) if method == "fetchmany" else (100,):
                observation = evaluate(connection, query, limit=limit, batch=batch, method=method)
                observation.details.update(
                    {"repeat": repeat + 1, "table": table.name, "selected_column_count": 1}
                )
                results.append(observation)
        try:
            sample = read(connection, query.sql, limit=1)
            if sample and sample[0][0] is not None:
                lookup = Query("filtered_lookup", query.sql + f" WHERE {c} = ?", (sample[0][0],))
                results.append(evaluate(connection, lookup, limit=limit))
            else:
                results.append(Observation("filtered_lookup", "not-tested"))
        except ReadError as error:
            results.append(failure("filtered_lookup", error))
    return results
