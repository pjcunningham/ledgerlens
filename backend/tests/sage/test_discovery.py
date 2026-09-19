import json
import struct
import traceback
from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from ledgerlens.sage import cli, connection, diagnostics
from ledgerlens.sage.benchmarks import benchmark
from ledgerlens.sage.capabilities import Query, capabilities, evaluate, queries
from ledgerlens.sage.config import SageError, SageSettings
from ledgerlens.sage.connection import ReadError, connect, read
from ledgerlens.sage.metadata import column_named, discover, identifier, table_named
from ledgerlens.sage.models import Column, Schema, Table
from ledgerlens.sage.profiling import observe_values, profile
from ledgerlens.sage.relationships import relationships, summarize
from ledgerlens.sage.reports import json_value, redact, report, sanitized_report, write_artifact

from .fakes import FakeConnection, FakeDriver, OdbcFailure


@pytest.fixture
def db():
    value = FakeConnection()
    yield value
    if not value.closed:
        value.close()


@pytest.fixture
def settings():
    return SageSettings(
        _env_file=None, dsn="private-dsn", username="private-user", password="secret;}"
    )


@pytest.mark.parametrize("timeout", [0, -1, 301, "invalid"])
def test_timeout_validation(timeout):
    with pytest.raises(ValidationError):
        SageSettings(_env_file=None, query_timeout_seconds=timeout)


def test_configuration_optional_and_secrets_redacted(settings, client):
    assert client.get("/api/health/live").status_code == 200
    assert "secret;}" not in repr(settings)
    assert "private-user" not in settings.model_dump_json()
    with pytest.raises(SageError, match="Configure"):
        SageSettings(_env_file=None, dsn="", username="").require_connection()


def test_missing_dependency(monkeypatch):
    def missing(name):
        raise ImportError("private details")

    monkeypatch.setattr(connection.importlib, "import_module", missing)
    with pytest.raises(SageError, match="uv sync --extra sage"):
        connection.load_driver()


@pytest.mark.parametrize("names,expected", [([], False), (["Other"], False), (["Sage v34"], True)])
def test_driver_diagnostics(monkeypatch, names, expected):
    driver = FakeDriver()
    driver.drivers = lambda: names
    monkeypatch.setattr(diagnostics, "load_driver", lambda: driver)
    result = diagnostics.drivers()
    assert result["sage_driver_present"] is expected
    assert result["architecture_bits"] == struct.calcsize("P") * 8
    assert result["drivers"] == names
    driver.connection.close()


def test_connection_lifecycle_and_escaping(settings):
    driver = FakeDriver()
    with connect(settings, driver) as handle:
        assert handle.timeout == 30
        assert diagnostics.probe(handle)["read_access"] == "OK"
        text, options = driver.arguments
        assert text.startswith("DSN=private-dsn;UID=private-user;")
        assert "PWD={secret;}}}" in text
        assert options == {"readonly": True, "autocommit": True, "timeout": 30}
    assert driver.connection.closed
    assert all(cursor.closed for cursor in driver.connection.cursors)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Sage DSN", "Sage DSN"),
        ("user", "user"),
        ("", ""),
        ("password;UID=evil", "{password;UID=evil}"),
        ("a}b", "{a}}b}"),
        (" padded ", "{ padded }"),
    ],
)
def test_driver_compatible_safe_attribute_encoding(value, expected):
    assert connection.escape(value) == expected


@pytest.mark.parametrize("state", ["28000", "08001", "HYT00"])
def test_connection_failure_does_not_leak(settings, state):
    driver = FakeDriver()

    def fail(*args, **kwargs):
        raise OdbcFailure(state, "secret;} private-dsn private-user C:/Company/ACCDATA")

    driver.connect = fail
    with pytest.raises(ReadError) as caught:
        with connect(settings, driver):
            pass
    rendered = "".join(traceback.format_exception(caught.value))
    assert state in str(caught.value)
    assert "secret;}" not in rendered
    assert "ACCDATA" not in rendered
    driver.connection.close()


def test_connection_closes_after_operation_error(settings):
    driver = FakeDriver()
    with pytest.raises(SageError):
        with connect(settings, driver):
            raise SageError("safe failure")
    assert driver.connection.closed


def test_driver_rejects_timeout_without_losing_read_access(settings):
    driver = FakeDriver()
    underlying = driver.connection

    class RejectTimeout:
        @property
        def timeout(self):
            return 0

        @timeout.setter
        def timeout(self, value):
            raise OdbcFailure("HY092", "private diagnostics")

        def close(self):
            underlying.close()

    driver.connection = RejectTimeout()
    with pytest.warns(RuntimeWarning, match="process deadline"):
        with connect(settings, driver) as handle:
            assert handle.timeout == 0
    assert underlying.closed


def test_timeout_unexpected_failure_closes_connection(settings):
    driver = FakeDriver()
    underlying = driver.connection

    class FailedTimeout:
        @property
        def timeout(self):
            return 0

        @timeout.setter
        def timeout(self, value):
            raise OdbcFailure("08003", "private")

        def close(self):
            underlying.close()

    driver.connection = FailedTimeout()
    with pytest.raises(ReadError):
        with connect(settings, driver):
            pytest.fail("Connection must not be yielded")
    assert underlying.closed


def test_metadata_ordering_and_unavailable_relations(db):
    schema = discover(db)
    assert [table.name for table in schema.tables] == ["INVOICE", "SALES_LEDGER"]
    assert schema == discover(db)
    table = table_named(schema, "SALES_LEDGER")
    assert table.columns[0].name == "ACCOUNT_REF"
    assert table.columns[0].size == 50
    statuses = {result.operation: result for result in table.metadata}
    assert statuses["foreign_keys"].status == "unsupported"
    assert statuses["primary_keys"].details["empty_not_proof_of_absence"]
    assert all(cursor.closed for cursor in db.cursors)


def test_table_enumeration_failure_sanitized(db):
    db.metadata_error = OdbcFailure("HY000", "private error")
    with pytest.raises(ReadError, match="HY000") as caught:
        discover(db)
    assert "private" not in str(caught.value)


def test_columns_metadata_failure_is_recorded(db, monkeypatch):
    from .fakes import FakeCursor

    def fail(*args, **kwargs):
        raise OdbcFailure("IM001", "private")

    monkeypatch.setattr(FakeCursor, "columns", fail)
    schema = discover(db)
    assert len(schema.tables) == 2
    assert all(table.metadata[0].status == "unsupported" for table in schema.tables)


def test_legacy_odbc2_column_names_preserve_precision_and_scale(db, monkeypatch):
    from .fakes import FakeCursor

    def legacy_columns(self, table):
        self.rows(
            [
                {
                    "table_name": table,
                    "column_name": "BALANCE",
                    "data_type": 8,
                    "type_name": "DOUBLE",
                    "precision": 15,
                    "length": 8,
                    "scale": 2,
                    "nullable": 0,
                }
            ]
        )

    monkeypatch.setattr(FakeCursor, "columns", legacy_columns)
    column = discover(db).tables[0].columns[0]
    assert (column.size, column.precision, column.buffer_length, column.scale) == (15, 15, 8, 2)
    assert column.ordinal is None  # Never invent an ordinal absent from metadata.


@pytest.mark.parametrize(
    "name", ["INVOICE; DROP TABLE X", "INVOICE--", "x.y", "[INVOICE]", "x y", "x\x00"]
)
def test_unsafe_identifiers_rejected(name):
    with pytest.raises(SageError, match="Malformed"):
        identifier(name)


def test_unknown_identifiers_rejected(db):
    schema = discover(db)
    with pytest.raises(SageError, match="Unknown table"):
        table_named(schema, "MISSING")
    with pytest.raises(SageError, match="Unknown column"):
        column_named(schema.tables[0], "MISSING")
    assert db.calls == []


@pytest.mark.parametrize("method", ["fetchone", "fetchmany", "iteration"])
def test_bounded_fetch_and_cursor_cleanup(db, method):
    rows = read(db, "SELECT ACCOUNT_REF FROM INVOICE", limit=2, method=method)
    assert len(rows) == 2
    assert all(cursor.closed for cursor in db.cursors)
    assert all(size <= 2 for size in db.fetch_sizes)


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM INVOICE",
        "SELECT 1; DELETE FROM X",
        "SELECT 1 -- comment",
        "SELECT * INTO NEW_TABLE FROM INVOICE",
    ],
)
def test_write_and_multiple_statements_rejected(db, sql):
    with pytest.raises(SageError):
        read(db, sql)
    assert db.calls == []


def test_capabilities_bind_values_and_record_failures(db):
    schema = discover(db)
    table = table_named(schema, "INVOICE")
    results = capabilities(db, table, schema)
    statuses = {result.operation: result.status for result in results}
    assert statuses["projection"] == "supported"
    assert statuses["top"] == "failed"  # syntax error is not automatically "unsupported"
    assert statuses["date_parameters"] == "not-tested"
    assert any(params == (1, 1) for _, params in db.calls)
    assert all("LedgerLensSyntheticProbe" not in sql for sql, _ in db.calls)
    db.read_error = OdbcFailure("HYC00", "private")
    assert evaluate(db, Query("test", "SELECT 1")).status == "unsupported"


def test_date_and_numeric_capability_templates():
    table = Table(
        "INVOICE",
        "TABLE",
        [Column("DATE", 91, "DATE", 10, 0, 1, 1), Column("AMOUNT", 3, "DECIMAL", 12, 2, 1, 2)],
    )
    suite = queries(table, Schema([table]))
    assert any(
        query.name == "date_parameters" and isinstance(query.parameters[0], date) for query in suite
    )
    assert any(query.name == "aggregate" for query in suite)


def test_profile_aggregate_only_and_partial_scope(db):
    results = profile(db, discover(db).tables, limit=1)
    serialized = json.dumps(json_value(results))
    for private in ("PRIVATE-A", "Private Customer", "456789"):
        assert private not in serialized
    assert results[0].details["sample_complete"] is False
    assert results[0].details["row_count"] == 3
    db.read_error = OdbcFailure("HYT00", "private failure")
    failed = profile(db, discover(db).tables)
    assert all(result.status == "failed" for result in failed)


def test_type_observations_without_text_or_monetary_values():
    values = [
        None,
        "Private Customer ",
        "é",
        "",
        Decimal("234.56"),
        1.25,
        date(1899, 12, 30),
        datetime(2024, 1, 2, 13),
    ]
    result = observe_values(values)
    assert result["trailing_spaces"] == 1
    assert result["non_ascii_strings"] == 1
    assert result["possible_sentinel_dates"] == 1
    assert "Decimal" in result["python_types"]
    assert "Private" not in json.dumps(result)
    assert "234.56" not in json.dumps(result)
    assert observe_values([0, 1, 2, "private"], coded=True)["other_code_count"] == 1


@pytest.mark.parametrize(
    "left,right,cardinality",
    [
        ([1], [1], "one-to-one"),
        ([1], [1, 1], "one-to-many"),
        ([1, 1], [1], "many-to-one"),
        ([1, 1], [1, 1], "potentially-many-to-many"),
        ([1], [2], "no-matches"),
    ],
)
def test_cardinality(left, right, cardinality):
    assert summarize(left, right, complete=True)["observed_cardinality"] == cardinality


def test_relationship_counts_and_no_raw_keys(db):
    results = relationships(db, discover(db), limit=100)
    details = results[0].details
    assert details["matched_left_rows"] == 2
    assert details["orphan_count"] == 1
    assert details["left_duplicate_excess"] == 1
    assert "PRIVATE" not in json.dumps(json_value(results))
    assert relationships(db, discover(db), limit=1)[0].details["orphan_count"] is None
    assert any(result.status == "not-tested" for result in results)


def test_benchmark_bounded_all_fetch_modes(db):
    schema = discover(db)
    results = benchmark(db, schema.tables[0], schema, limit=2, repeats=1)
    sequential = [result for result in results if result.operation == "sequential_read"]
    assert {result.details["fetch_method"] for result in sequential} == {
        "iteration",
        "fetchone",
        "fetchmany",
    }
    assert {result.details["batch_size"] for result in sequential} == {100, 500, 1000, 5000}
    assert all(result.details["fetched_count"] <= 2 for result in sequential)
    assert "PRIVATE" not in json.dumps(json_value(results))


def test_reports_deterministic_and_private_fields_excluded(tmp_path, settings):
    artifacts = {
        "environment": {
            "python": "3.14.3",
            "sage_build": "private company",
            "password": "secret;}",
        },
        "schema": {"tables": [{"name": "SALES_LEDGER", "customer": "Private Customer"}]},
        "profile": [
            {
                "operation": "SALES_LEDGER",
                "status": "supported",
                "details": {"row_count": 2, "private": "PRIVATE-A"},
            }
        ],
    }
    result = sanitized_report(artifacts)
    assert result == sanitized_report(artifacts)
    assert "Private Customer" not in result and "PRIVATE-A" not in result
    assert "secret;}" not in result and "private company" not in result
    assert "3.14.3" in result
    write_artifact(tmp_path, "environment", artifacts["environment"], settings)
    assert "secret;}" not in (tmp_path / "environment.json").read_text()
    assert report(tmp_path) == (tmp_path / "report.md").read_text()


@pytest.mark.parametrize("command", cli.COMMANDS)
def test_all_commands_have_help(command, capsys):
    with pytest.raises(SystemExit) as exit_status:
        cli.main([command, "--help"])
    assert exit_status.value.code == 0
    assert "--help" in capsys.readouterr().out


def test_cli_missing_configuration(monkeypatch, capsys):
    monkeypatch.setattr(
        cli, "SageSettings", lambda: SageSettings(_env_file=None, dsn="", username="")
    )
    assert cli.guarded_execute(cli.parser().parse_args(["probe"])) == 1
    assert "Configure" in capsys.readouterr().err


def test_cli_artifacts_and_environment_guard(monkeypatch, tmp_path, settings):
    monkeypatch.setattr(cli, "ARTIFACT_ROOT", tmp_path)
    monkeypatch.setattr(cli, "SageSettings", lambda: settings)
    monkeypatch.setattr(cli, "load_driver", FakeDriver)
    output = tmp_path / "run"
    for command in (
        "probe",
        "schema",
        "capabilities",
        "profile",
        "relationships",
        "benchmark",
        "report",
    ):
        args = cli.parser().parse_args([command, "--output", str(output)])
        assert cli.execute(args) == 0
    for file in output.iterdir():
        assert "PRIVATE-A" not in file.read_text()
        assert "secret;}" not in file.read_text()
    with pytest.raises(SageError, match="different environment"):
        cli.execute(
            cli.parser().parse_args(["probe", "--output", str(output), "--sage-build", "34.1"])
        )


def test_artifact_path_cannot_escape_ignored_root(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "ARTIFACT_ROOT", tmp_path / "artifacts")
    with pytest.raises(SageError, match="ignored"):
        cli.output_directory(tmp_path / "tracked")


def test_watchdog_stops_unresponsive_worker(monkeypatch, capsys):
    class Process:
        alive = True
        exitcode = None

        def start(self):
            pass

        def join(self, timeout):
            pass

        def is_alive(self):
            return self.alive

        def terminate(self):
            self.alive = False

    process = Process()

    class Context:
        def Process(self, **kwargs):
            return process

    monkeypatch.setattr(cli.multiprocessing, "get_context", lambda kind: Context())
    assert cli.main(["probe", "--deadline-seconds", "1"]) == 1
    assert not process.alive
    assert "deadline exceeded" in capsys.readouterr().err


def test_nullable_relationship_and_incomplete_reads():
    result = summarize([None, "private", "private", "missing"], ["private"], complete=False)
    assert result["left_nonnull"] == 3
    assert result["matched_left_rows"] == 2
    assert result["unmatched_left_rows_in_sample"] == 1
    assert result["orphan_count"] is None
    assert "private" not in json.dumps(result)


@pytest.mark.parametrize("username,password", [("a", "a"), ("s", "1"), ("name", "status")])
def test_short_credentials_preserve_structure_and_environment(
    monkeypatch, tmp_path, username, password
):
    settings = SageSettings(
        _env_file=None, dsn="synthetic-dsn", username=username, password=password
    )
    structural = {
        "name": "SALES_LEDGER",
        "status": "supported",
        "fingerprint": "a1status",
        "driver_version": "34.0.23.0 Sage",
        "columns": [{"name": "ACCOUNT_REF"}],
    }
    assert redact(structural, settings) == structural
    private = {"username": username, "password": password, "message": "C:/Company/ACCDATA"}
    assert redact(private, settings) == dict.fromkeys(private, "[redacted]")
    monkeypatch.setattr(cli, "ARTIFACT_ROOT", tmp_path)
    monkeypatch.setattr(cli, "SageSettings", lambda: settings)
    monkeypatch.setattr(cli, "load_driver", FakeDriver)
    output = tmp_path / "run"
    args = cli.parser().parse_args(["probe", "--output", str(output)])
    assert cli.execute(args) == 0
    first = json.loads((output / "environment.json").read_text())["fingerprint"]
    args = cli.parser().parse_args(["profile", "--output", str(output)])
    assert cli.execute(args) == 0
    assert json.loads((output / "environment.json").read_text())["fingerprint"] == first
    assert "SALES_LEDGER" in report(output)


@pytest.mark.parametrize(
    "count_fails,sample_fails", [(False, False), (True, False), (False, True), (True, True)]
)
def test_profile_independent_outcomes(db, monkeypatch, count_fails, sample_fails):
    from .fakes import FakeCursor

    original = FakeCursor.execute

    def execute(self, sql, parameters=()):
        counting = "COUNT(*)" in sql
        if (counting and count_fails) or (not counting and sample_fails):
            raise OdbcFailure("HYT00" if counting else "42000", "Private Customer password")
        return original(self, sql, parameters)

    monkeypatch.setattr(FakeCursor, "execute", execute)
    observations = profile(db, [table_named(discover(db), "SALES_LEDGER")], limit=1)
    details = observations[0].details
    assert details["count"]["status"] == ("failed" if count_fails else "supported")
    assert details["sample"]["status"] == ("failed" if sample_fails else "supported")
    rendered = sanitized_report({"profile": json_value(observations)})
    assert f"count: {'failed' if count_fails else 'supported'}" in rendered
    assert f"sample: {'failed' if sample_fails else 'supported'}" in rendered
    if count_fails:
        assert "SQLSTATE: HYT00" in rendered
    else:
        assert details["count"]["row_count"] == 2
    if sample_fails:
        assert "SQLSTATE: 42000" in rendered
    else:
        assert details["sample"]["row_count"] == 1
        assert "row_count: 1" in rendered
    assert "Private" not in rendered and "password" not in rendered


def test_report_modes_are_mutually_exclusive():
    with pytest.raises(SystemExit) as error:
        cli.parser().parse_args(["report", "--sanitized", "--local-detail"])
    assert error.value.code == 2


def test_artifact_provenance_exposes_interrupted_rerun(monkeypatch, tmp_path, settings):
    monkeypatch.setattr(cli, "ARTIFACT_ROOT", tmp_path)
    monkeypatch.setattr(cli, "SageSettings", lambda: settings)
    monkeypatch.setattr(cli, "load_driver", FakeDriver)
    output = tmp_path / "run"
    args = cli.parser().parse_args(["profile", "--limit", "1", "--output", str(output)])
    cli.execute(args)
    first = json.loads((output / "profile.provenance.json").read_text())
    assert first["completion"] == "complete" and first["sample_limit"] == 1
    assert first["command"] == "profile" and first["timestamp"]
    assert first["selected_tables"] == ["INVOICE", "SALES_LEDGER"]
    original = cli.profile_table

    def interrupt(connection, table, limit):
        if table.name == "SALES_LEDGER":
            raise SageError("Simulated interrupted run")
        return original(connection, table, limit)

    monkeypatch.setattr(cli, "profile_table", interrupt)
    with pytest.raises(SageError, match="interrupted"):
        cli.execute(args)
    second = json.loads((output / "profile.provenance.json").read_text())
    assert second["completion"] == "partial" and second["completed_tables"] == 1
    assert first["run_id"] != second["run_id"]
    rendered = report(output)
    assert "completion=partial" in rendered
    assert "provenance unavailable" in rendered
    sources = json.loads((output / "report.provenance.json").read_text())["sources"]
    assert sources["profile"] == second
