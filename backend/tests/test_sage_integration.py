"""Opt-in sequential live checks with a separate driver-hang deadline."""

import multiprocessing

import pytest

from ledgerlens.sage.config import SageError, SageSettings
from ledgerlens.sage.connection import connect, read
from ledgerlens.sage.diagnostics import probe
from ledgerlens.sage.metadata import column_named, discover, metadata_rows
from ledgerlens.sage.models import PRIORITY_TABLES

pytestmark = pytest.mark.sage_integration


def live_worker(name, sender):
    try:
        settings = SageSettings()
        settings.require_connection()
        with connect(settings) as connection:
            assert probe(connection)["read_access"] == "OK"
            if name is None:
                assert discover(connection).tables
            else:
                names = {row.get("table_name") for row in metadata_rows(connection, "tables")}
                if name not in names:
                    sender.send(("skip", "Priority table not exposed by this Sage edition"))
                    return
                schema = discover(connection, only=name)
                table = next(table for table in schema.tables if table.name == name)
                assert table.columns
                column = column_named(table, table.columns[0].name)
                assert len(read(connection, f"SELECT {column} FROM {table.name}", limit=10)) <= 10
        sender.send(("pass", "Read-only check passed"))
    except SageError as error:
        sender.send(("fail", str(error)))
    except Exception:
        sender.send(("fail", "Live metadata/read check failed; no private details emitted"))
    finally:
        sender.close()


def run_live_check(name=None):
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=live_worker, args=(name, sender))
    process.start()
    sender.close()
    try:
        process.join(60)
        if process.is_alive():
            pytest.fail("Live Sage check exceeded its 60-second deadline")
        assert process.exitcode == 0 and receiver.poll(), "Live worker exited without a result"
        status, message = receiver.recv()
        if status == "skip":
            pytest.skip(message)
        assert status == "pass", message
    finally:
        if process.is_alive():
            process.terminate()
            process.join(5)
            if process.is_alive():
                process.kill()
                process.join(5)
        receiver.close()


def test_live_connection_and_schema():
    run_live_check()


@pytest.mark.parametrize("name", PRIORITY_TABLES)
def test_live_priority_bounded_read(name):
    run_live_check(name)
