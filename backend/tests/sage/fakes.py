"""A DB-API fake at the pyodbc boundary, backed by synthetic in-memory SQLite."""

import sqlite3


class OdbcFailure(Exception):
    pass


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.handle = connection.db.cursor()
        self.arraysize = 1
        self.description = []
        self.metadata = None
        self.closed = False

    def execute(self, sql, parameters=()):
        self.connection.calls.append((sql, parameters))
        if self.connection.read_error:
            raise self.connection.read_error
        try:
            self.handle.execute(sql, parameters)
            self.description = self.handle.description
        except sqlite3.Error:
            raise OdbcFailure("42000", "private error with company path and password") from None
        return self

    def rows(self, rows):
        self.description = [(key,) for key in rows[0]] if rows else []
        self.metadata = [tuple(row.values()) for row in rows]

    def tables(self):
        if self.connection.metadata_error:
            raise self.connection.metadata_error
        self.rows(
            [
                {"table_name": name, "table_type": "TABLE"}
                for name in reversed(list(self.connection.columns))
            ]
        )

    def columns(self, table):
        self.rows(
            [
                {
                    "table_name": table,
                    "column_name": name,
                    "data_type": kind,
                    "type_name": "VARCHAR" if kind == 12 else "INTEGER",
                    "column_size": 50,
                    "decimal_digits": 0,
                    "nullable": 1,
                    "ordinal_position": index + 1,
                }
                for index, (name, kind) in enumerate(self.connection.columns[table])
            ]
        )

    def primaryKeys(self, **kwargs):
        self.rows([])

    def foreignKeys(self, **kwargs):
        raise OdbcFailure("IM001", "private unsupported diagnostics")

    def statistics(self, **kwargs):
        self.rows([])

    def fetchone(self):
        if self.metadata is not None:
            return self.metadata.pop(0) if self.metadata else None
        return self.handle.fetchone()

    def fetchmany(self, size):
        self.connection.fetch_sizes.append(size)
        if self.metadata is not None:
            rows, self.metadata = self.metadata[:size], self.metadata[size:]
            return rows
        return self.handle.fetchmany(size)

    def __iter__(self):
        while (row := self.fetchone()) is not None:
            yield row

    def close(self):
        self.closed = True
        self.handle.close()


class FakeConnection:
    def __init__(self):
        self.timeout = 0
        self.closed = False
        self.calls = []
        self.fetch_sizes = []
        self.cursors = []
        self.read_error = None
        self.metadata_error = None
        self.columns = {
            "SALES_LEDGER": [("ACCOUNT_REF", 12), ("NAME", 12), ("ACTIVE", 4)],
            "INVOICE": [("ACCOUNT_REF", 12), ("INVOICE_NUMBER", 4)],
        }
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("""
            CREATE TABLE SALES_LEDGER (ACCOUNT_REF TEXT, NAME TEXT, ACTIVE INTEGER);
            CREATE TABLE INVOICE (ACCOUNT_REF TEXT, INVOICE_NUMBER INTEGER);
            INSERT INTO SALES_LEDGER VALUES ('PRIVATE-A', 'Private Customer', 1);
            INSERT INTO SALES_LEDGER VALUES ('PRIVATE-B', 'Private Person', 0);
            INSERT INTO INVOICE VALUES ('PRIVATE-A', 456789);
            INSERT INTO INVOICE VALUES ('PRIVATE-A', 456790);
            INSERT INTO INVOICE VALUES ('PRIVATE-ORPHAN', 456791);
        """)

    def cursor(self):
        cursor = FakeCursor(self)
        self.cursors.append(cursor)
        return cursor

    def getinfo(self, code):
        return {6: "Sage-test.dll", 7: "34.0.0", 10: "03.80", 17: "Sage", 18: "34"}[code]

    def close(self):
        self.closed = True
        self.db.close()


class FakeDriver:
    version = "5.3.0"

    def __init__(self):
        self.connection = FakeConnection()
        self.arguments = None

    def drivers(self):
        return ["Sage Line 50 v34", "Other driver"]

    def connect(self, text, **kwargs):
        self.arguments = (text, kwargs)
        return self.connection
