"""The only pyodbc boundary. Rows are copied; driver text is never propagated."""

import importlib
import re
import warnings
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Protocol, cast

from ledgerlens.sage.config import SageError, SageSettings


class Cursor(Protocol):
    arraysize: int
    description: Sequence[Sequence[object]]

    def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> object: ...
    def fetchone(self) -> Sequence[object] | None: ...
    def fetchmany(self, size: int) -> Sequence[Sequence[object]]: ...
    def __iter__(self) -> Iterator[Sequence[object]]: ...
    def tables(self, **kwargs: object) -> object: ...
    def columns(self, **kwargs: object) -> object: ...
    def primaryKeys(self, **kwargs: object) -> object: ...
    def foreignKeys(self, **kwargs: object) -> object: ...
    def statistics(self, **kwargs: object) -> object: ...
    def close(self) -> None: ...


class Connection(Protocol):
    timeout: int

    def cursor(self) -> Cursor: ...
    def getinfo(self, code: int) -> object: ...
    def close(self) -> None: ...


class Driver(Protocol):
    version: str

    def drivers(self) -> list[str]: ...
    def dataSources(self) -> dict[str, str]: ...
    def connect(
        self, connection_string: str, *, timeout: int, readonly: bool, autocommit: bool
    ) -> Connection: ...


def load_driver() -> Driver:
    try:
        return cast(Driver, importlib.import_module("pyodbc"))
    except ImportError, OSError:
        raise SageError("pyodbc unavailable. On Windows run: uv sync --extra sage") from None


def sqlstate(error: Exception) -> str | None:
    value = error.args[0] if error.args else None
    return value if isinstance(value, str) and re.fullmatch(r"[A-Z0-9]{5}", value) else None


class ReadError(SageError):
    def __init__(self, error: Exception):
        self.state = sqlstate(error)
        super().__init__("ODBC read failed" + (f" (SQLSTATE {self.state})" if self.state else ""))


def escape(value: str) -> str:
    # Sage v34 treats unnecessary braces as literal DSN/credential characters.
    # Values needing protection still use ODBC escaping; never interpolate delimiters.
    if value == value.strip() and not any(char in value for char in ";{}=\x00\r\n"):
        return value
    return "{" + value.replace("}", "}}") + "}"


@contextmanager
def connect(settings: SageSettings, driver: Driver | None = None) -> Iterator[Connection]:
    settings.require_connection()
    driver = driver or load_driver()
    connection = None
    try:
        values = (settings.dsn, settings.username, settings.password)
        text = ";".join(
            f"{key}={escape(value.get_secret_value())}"
            for key, value in zip(("DSN", "UID", "PWD"), values, strict=True)
        )
        connection = driver.connect(
            text, timeout=settings.query_timeout_seconds, readonly=True, autocommit=True
        )
        try:
            connection.timeout = settings.query_timeout_seconds
        except Exception as error:
            if sqlstate(error) not in {"HY092", "HYC00", "IM001"}:
                raise
            warnings.warn(
                "Sage driver rejected query timeout; use the CLI process deadline.",
                RuntimeWarning,
                stacklevel=2,
            )
    except Exception as error:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                raise SageError("Query timeout setup and connection cleanup failed.") from None
        raise ReadError(error) from None
    try:
        yield connection
    finally:
        try:
            connection.close()
        except Exception:
            raise SageError("ODBC connection cleanup failed.") from None


@contextmanager
def cursor(connection: Connection) -> Iterator[Cursor]:
    handle = None
    try:
        handle = connection.cursor()
        yield handle
    except SageError:
        raise
    except Exception as error:
        raise ReadError(error) from None
    finally:
        if handle is not None:
            try:
                handle.close()
            except Exception:
                raise SageError("ODBC cursor cleanup failed.") from None


def read(
    connection: Connection,
    sql: str,
    parameters: tuple[object, ...] = (),
    *,
    limit: int = 100,
    batch: int = 100,
    method: str = "fetchmany",
) -> list[tuple[object, ...]]:
    # Only internal query builders call this function; no SQL CLI input exists.
    forbidden = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "CREATE",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "INTO",
        "EXEC",
        "EXECUTE",
        "CALL",
        "MERGE",
    }
    if (
        not sql.startswith("SELECT ")
        or any(token in sql for token in (";", "--", "/*"))
        or forbidden.intersection(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", sql.upper()))
    ):
        raise SageError("Only a single code-defined SELECT is allowed.")
    if not 1 <= limit <= 10001 or not 1 <= batch <= 5000:
        raise SageError("Read bounds must be between 1 and 10001; batches at most 5000.")
    result: list[tuple[object, ...]] = []
    with cursor(connection) as handle:
        handle.arraysize = batch
        handle.execute(sql, parameters)
        if method == "iteration":
            for row in handle:
                result.append(tuple(row))
                if len(result) == limit:
                    break
        elif method == "fetchone":
            while len(result) < limit:
                single = handle.fetchone()
                if single is None:
                    break
                result.append(tuple(single))
        else:
            while len(result) < limit:
                rows = handle.fetchmany(min(batch, limit - len(result)))
                if not rows:
                    break
                result.extend(tuple(row) for row in rows)
    return result
