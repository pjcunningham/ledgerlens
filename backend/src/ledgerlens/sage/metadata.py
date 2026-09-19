import re

from ledgerlens.sage.config import SageError
from ledgerlens.sage.connection import Connection, ReadError, cursor
from ledgerlens.sage.models import Column, Json, Observation, Schema, Table


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", value):
        raise SageError("Malformed ODBC identifier; no query was issued.")
    return value


def table_named(schema: Schema, name: str) -> Table:
    identifier(name)
    for table in schema.tables:
        if table.name == name:
            return table
    raise SageError("Unknown table; select a discovered table name.")


def column_named(table: Table, name: str) -> str:
    identifier(name)
    if name not in {column.name for column in table.columns}:
        raise SageError("Unknown column; select a discovered column name.")
    return name


def failure(operation: str, error: ReadError) -> Observation:
    state = error.state
    unsupported = state is not None and (state.startswith("0A") or state in {"IM001", "HYC00"})
    return Observation(operation, "unsupported" if unsupported else "failed", state)


def metadata_rows(
    connection: Connection, operation: str, table: str | None = None
) -> list[dict[str, object]]:
    with cursor(connection) as handle:
        if operation == "tables":
            handle.tables()
        elif operation == "columns":
            handle.columns(table=table)
        elif operation == "primary_keys":
            handle.primaryKeys(table=table)
        elif operation == "foreign_keys":
            handle.foreignKeys(foreignTable=table)
        elif operation == "indexes":
            handle.statistics(table=table, unique=False, quick=True)
        else:
            raise SageError("Unknown metadata operation.")
        names = [str(column[0]).lower() for column in handle.description]
        result = []
        for row in handle:
            result.append(dict(zip(names, row, strict=True)))
            if len(result) > 100000:
                raise SageError("Metadata safety limit exceeded.")
        return result


def integer(value: object) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def discover(connection: Connection, only: str | None = None) -> Schema:
    rows = metadata_rows(connection, "tables")
    schema = Schema([])
    names: set[str] = set()
    for row in sorted(rows, key=lambda row: str(row.get("table_name"))):
        name = text(row.get("table_name"))
        if name is None or row.get("table_type") not in {"TABLE", "VIEW"}:
            continue
        try:
            identifier(name)
        except SageError:
            schema.observations.append(Observation("unsafe_table_identifier", "not-tested"))
            continue
        if name in names:
            raise SageError("Ambiguous table names across catalogs/schemas; discovery stopped.")
        names.add(name)
        schema.tables.append(Table(name, str(row["table_type"])))
    if only is not None:
        selected = [table_named(schema, only)]
    else:
        selected = schema.tables
    for table in selected:
        try:
            columns = metadata_rows(connection, "columns", table.name)
            for row in columns:
                # SQLColumns uses patterns: underscores may also match other tables.
                if row.get("table_name") != table.name:
                    continue
                name = text(row.get("column_name"))
                if name is None:
                    continue
                try:
                    identifier(name)
                except SageError:
                    table.metadata.append(Observation("unsafe_column_identifier", "not-tested"))
                    continue
                table.columns.append(
                    Column(
                        name,
                        integer(row.get("data_type")),
                        text(row.get("type_name")),
                        integer(row.get("column_size", row.get("precision"))),
                        integer(row.get("decimal_digits", row.get("scale"))),
                        integer(row.get("nullable")),
                        integer(row.get("ordinal_position")),
                        integer(row.get("column_size", row.get("precision")))
                        if integer(row.get("data_type")) in {2, 3, 4, 5, 6, 7, 8, -5, -6, 65530}
                        else None,
                        integer(row.get("buffer_length", row.get("length"))),
                    )
                )
            table.columns.sort(key=lambda column: (column.ordinal or 0, column.name))
            table.metadata.append(
                Observation(
                    "columns",
                    "supported",
                    details={"reported_count": len(table.columns), "empty": not table.columns},
                )
            )
        except ReadError as error:
            table.metadata.append(failure("columns", error))
        for operation, allowed in (
            ("primary_keys", ("column_name", "key_seq")),
            (
                "foreign_keys",
                ("pktable_name", "pkcolumn_name", "fktable_name", "fkcolumn_name", "key_seq"),
            ),
            ("indexes", ("column_name", "non_unique", "type", "ordinal_position", "asc_or_desc")),
        ):
            try:
                rows = metadata_rows(connection, operation, table.name)
                records: list[Json] = []
                for row in rows:
                    record: dict[str, Json] = {}
                    for key in allowed:
                        value = row.get(key)
                        if isinstance(value, (str, int, bool)) or value is None:
                            record[key] = value
                    records.append(record)
                records.sort(key=str)
                table.metadata.append(
                    Observation(
                        operation,
                        "supported",
                        details={
                            "declared_metadata": records,
                            "empty_not_proof_of_absence": not records,
                        },
                    )
                )
            except ReadError as error:
                table.metadata.append(failure(operation, error))
    return schema
