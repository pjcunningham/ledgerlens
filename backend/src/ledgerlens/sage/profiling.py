from datetime import date, datetime
from decimal import Decimal

from ledgerlens.sage.connection import Connection, ReadError, read
from ledgerlens.sage.metadata import column_named, identifier
from ledgerlens.sage.models import FLAGS, KEYS, Json, Observation, Table


def type_name(value: object) -> str:
    for kind in (bool, datetime, date, Decimal, int, float, str, bytes):
        if isinstance(value, kind):
            return kind.__name__
    return "NoneType" if value is None else "other"


def observe_values(
    values: list[object], *, coded: bool = False, key: bool = False
) -> dict[str, Json]:
    nonnull = [value for value in values if value is not None]
    result: dict[str, Json] = {
        "sample_count": len(values),
        "null_count": len(values) - len(nonnull),
        "python_types": [name for name in sorted({type_name(value) for value in values})],
    }
    strings = [value for value in nonnull if isinstance(value, str)]
    if strings:
        result.update(
            {
                "empty_strings": sum(value == "" for value in strings),
                "trailing_spaces": sum(value.endswith(" ") for value in strings),
                "non_ascii_strings": sum(not value.isascii() for value in strings),
                "maximum_observed_length": max(map(len, strings)),
            }
        )
    dates = [value for value in nonnull if isinstance(value, date)]
    if dates:
        result.update(
            {
                "earliest_date": min(value.isoformat() for value in dates),
                "latest_date": max(value.isoformat() for value in dates),
                "non_midnight_times": sum(
                    isinstance(value, datetime) and value.time().isoformat() != "00:00:00"
                    for value in dates
                ),
                "possible_sentinel_dates": sum(value.year <= 1900 for value in dates),
                "sentinel_interpretation": "heuristic only; verify against Sage",
            }
        )
    if coded:
        # Unknown codes are counted, never copied into artifacts.
        result["coded_distribution"] = {
            str(code): sum(value == code for value in nonnull) for code in (0, 1, 2)
        }
        result["other_code_count"] = sum(value not in (0, 1, 2) for value in nonnull)
    if key:
        supported = [
            value for value in nonnull if isinstance(value, (str, int, float, Decimal, date, bytes))
        ]
        result["distinct_nonnull_keys"] = len(set(supported))
        result["duplicate_excess"] = len(supported) - len(set(supported))
        result["unhandled_key_types"] = len(nonnull) - len(supported)
    return result


def profile_table(connection: Connection, table: Table, limit: int = 100) -> Observation:
    name = identifier(table.name)
    result = Observation(name, "supported", details={"column_count": len(table.columns)})
    count_outcome: dict[str, Json] = {"status": "supported"}
    sample_outcome: dict[str, Json] = {"status": "not-tested"}
    result.details.update({"count": count_outcome, "sample": sample_outcome})
    try:
        count = read(connection, f"SELECT COUNT(*) FROM {name}", limit=1)
        result.details["row_count"] = int(str(count[0][0])) if count else None
        count_outcome["row_count"] = result.details["row_count"]
    except ReadError as error:
        count_outcome.update({"status": "failed", "sqlstate": error.state})
        result.status = "failed"
    if not table.columns:
        result.status = "not-tested"
        return result
    # Keep the projected row width bounded too; identifiers/dates/numeric/flags first.
    structural = KEYS | FLAGS | {"RECORD_CREATE_DATE", "RECORD_MODIFY_DATE"}
    ordered = sorted(table.columns, key=lambda c: (c.name not in structural, c.ordinal or 0))[:32]
    projection = ", ".join(column_named(table, column.name) for column in ordered)
    try:
        rows = read(connection, f"SELECT {projection} FROM {name}", limit=limit + 1)
        complete = len(rows) <= limit
        rows = rows[:limit]
        sample_outcome.update({"status": "supported", "row_count": len(rows)})
        result.details.update(
            {
                "sample_complete": complete,
                "sample_limit": limit,
                "scope": "bounded sample; distinct/null/date observations are sample-only",
                "columns": {
                    column.name: observe_values(
                        [row[index] for row in rows],
                        coded=column.name in FLAGS,
                        key=column.name in KEYS,
                    )
                    for index, column in enumerate(ordered)
                },
                "potential_change_fields": [
                    column.name
                    for column in table.columns
                    if set(column.name.split("_"))
                    & {"MODIFIED", "MODIFY", "UPDATED", "DATE", "DELETED", "SEQUENCE"}
                ],
            }
        )
    except ReadError as error:
        sample_outcome.update({"status": "failed", "sqlstate": error.state})
        result.status = "failed"
    return result


def profile(connection: Connection, tables: list[Table], limit: int = 100) -> list[Observation]:
    return [profile_table(connection, table, limit) for table in tables]
