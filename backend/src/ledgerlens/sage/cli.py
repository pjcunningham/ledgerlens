import argparse
import hashlib
import json
import multiprocessing
import sys
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from ledgerlens.sage.benchmarks import benchmark
from ledgerlens.sage.capabilities import capabilities
from ledgerlens.sage.config import SageError, SageSettings
from ledgerlens.sage.connection import connect, load_driver
from ledgerlens.sage.diagnostics import drivers, environment, probe
from ledgerlens.sage.metadata import discover, table_named
from ledgerlens.sage.models import LINKS, PRIORITY_TABLES, Json
from ledgerlens.sage.profiling import profile_table
from ledgerlens.sage.relationships import relationships
from ledgerlens.sage.reports import json_value, redact, report, write_artifact, write_provenance

ARTIFACT_ROOT = Path(__file__).resolve().parents[4] / "artifacts" / "sage"
COMMANDS = (
    "drivers",
    "probe",
    "schema",
    "describe-table",
    "capabilities",
    "profile",
    "relationships",
    "benchmark",
    "report",
)


def bounded_integer(value: str) -> int:
    try:
        result = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Expected an integer.") from None
    if not 1 <= result <= 10000:
        raise argparse.ArgumentTypeError("Expected an integer from 1 to 10000.")
    return result


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Read-only Sage discovery; no records are exported.")
    commands = root.add_subparsers(dest="command", required=True)
    for command in COMMANDS:
        child = commands.add_parser(command, help=f"{command}: metadata/aggregate discovery only")
        child.add_argument("--output", type=Path, help="Local directory inside artifacts/sage")
        child.add_argument(
            "--sage-version", default="", help="Exact application version from Help > About"
        )
        child.add_argument(
            "--sage-build", default="", help="Exact application build from Help > About"
        )
        child.add_argument(
            "--sage-data-version", default="", help="Data version if Sage displays it"
        )
        child.add_argument(
            "--deadline-seconds",
            type=bounded_integer,
            default=300,
            help="Whole-command worker deadline; default 300",
        )
        if command == "describe-table":
            child.add_argument("table")
        elif command in {"capabilities", "profile", "benchmark"}:
            child.add_argument(
                "--table", help="Discovered table; defaults to available priority tables"
            )
        if command in {"profile", "relationships", "benchmark"}:
            child.add_argument(
                "--limit",
                type=bounded_integer,
                default=100,
                help="Maximum sampled rows per table; default 100",
            )
        if command == "benchmark":
            child.add_argument("--repeats", type=int, choices=(1, 2, 3), default=2)
        if command == "report":
            mode = child.add_mutually_exclusive_group()
            mode.add_argument(
                "--sanitized",
                action="store_true",
                default=True,
                help="Allowlisted public summary (default)",
            )
            mode.add_argument(
                "--local-detail",
                action="store_true",
                help="Local metadata/aggregate detail; never commit",
            )
    return root


def output_directory(path: Path | None, fingerprint: str = "") -> Path:
    directory = path.resolve() if path else ARTIFACT_ROOT / fingerprint
    if (
        not directory.resolve().is_relative_to(ARTIFACT_ROOT.resolve())
        or directory == ARTIFACT_ROOT
    ):
        raise SageError("Choose a run directory inside the ignored artifacts/sage directory.")
    return directory


def execute(args: argparse.Namespace) -> int:
    if args.command == "report":
        if args.output is None:
            raise SageError("report requires --output pointing to a discovery run directory.")
        print(report(output_directory(args.output), sanitized=not args.local_detail))
        return 0
    settings = SageSettings()
    if args.command == "drivers":
        print(json.dumps(redact(json_value(drivers()), settings), indent=2))
        return 0
    settings.require_connection()
    driver = load_driver()
    manual = {
        "sage_version": args.sage_version,
        "sage_build": args.sage_build,
        "sage_data_version": args.sage_data_version,
    }
    env = environment(driver, manual)
    print(
        "Opening read-only Sage connection; command deadline is enforced by the parent process.",
        file=sys.stderr,
    )
    with connect(settings, driver) as connection:
        env.update(probe(connection))
        env["query_timeout_seconds_requested"] = settings.query_timeout_seconds
        identity = [
            settings.dsn.get_secret_value(),
            driver.version,
            str(env.get("driver_version")),
            *manual.values(),
        ]
        fingerprint = hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:20]
        directory = output_directory(args.output, fingerprint)
        existing = directory / "environment.json"
        if existing.exists():
            previous = json.loads(existing.read_text(encoding="utf-8"))
            if previous.get("fingerprint") != fingerprint:
                raise SageError(
                    "Run directory belongs to a different environment; use a new directory."
                )
        env["fingerprint"] = fingerprint
        provenance: dict[str, Json] = {
            "timestamp": env["timestamp"],
            "command": args.command,
            "run_id": uuid4().hex,
            "fingerprint": fingerprint,
            "selected_tables": [],
            "sample_limit": getattr(args, "limit", None),
            "repeats": getattr(args, "repeats", None),
            "deadline_seconds": args.deadline_seconds,
            "completion": "complete",
        }
        write_artifact(directory, "environment", env, settings, provenance)
        if args.command == "probe":
            print("Connection and metadata read OK. Environment recorded; no credentials printed.")
            return 0
        print("Enumerating schema metadata (driver support may vary).", file=sys.stderr)
        if args.command != "describe-table":
            write_provenance(directory, "schema", {**provenance, "completion": "in-progress"})
        schema = discover(connection, args.table if args.command == "describe-table" else None)
        if args.command == "describe-table":
            print(
                json.dumps(redact(json_value(table_named(schema, args.table)), settings), indent=2)
            )
            return 0
        write_artifact(
            directory,
            "schema",
            schema,
            settings,
            {
                **provenance,
                "selected_tables": [table.name for table in schema.tables],
            },
        )
        if args.command == "schema":
            print(f"Schema recorded: {len(schema.tables)} tables/views.")
            return 0
        if args.command == "relationships":
            provenance["selected_tables"] = json_value(
                sorted(
                    {name for link in LINKS for name in (link.left_table, link.right_table)}
                    & {table.name for table in schema.tables}
                )
            )
            write_provenance(
                directory, "relationships", {**provenance, "completion": "in-progress"}
            )
            print(
                "Testing bounded relationship samples; incomplete samples do not prove orphans.",
                file=sys.stderr,
            )
            observations = relationships(connection, schema, args.limit)
            artifact = "relationships"
        else:
            tables = (
                [table_named(schema, args.table)]
                if args.table
                else [table for table in schema.tables if table.name in PRIORITY_TABLES]
            )
            if not tables:
                raise SageError(
                    "No priority tables found; inspect schema and select --table explicitly."
                )
            observations = []
            provenance["selected_tables"] = [
                table.name for table in (tables if args.command == "profile" else tables[:1])
            ]
            if args.command == "capabilities":
                provenance["sample_limit"] = 10
            artifact = "benchmarks" if args.command == "benchmark" else args.command
            write_provenance(directory, artifact, {**provenance, "completion": "in-progress"})
            if args.command == "profile":
                for index, table in enumerate(tables):
                    print(
                        f"Profiling table {index + 1}/{len(tables)}; COUNT may scan the table.",
                        file=sys.stderr,
                    )
                    observations.append(profile_table(connection, table, args.limit))
                    # Preserve completed tables if a later driver call reaches the deadline.
                    write_artifact(
                        directory,
                        "profile",
                        observations,
                        settings,
                        {
                            **provenance,
                            "completion": "partial",
                            "completed_tables": index + 1,
                        },
                    )
                artifact = "profile"
            elif args.command == "capabilities":
                observations = capabilities(connection, tables[0], schema)
                artifact = "capabilities"
            else:
                print("Running explicitly requested single-connection benchmarks.", file=sys.stderr)
                observations = benchmark(connection, tables[0], schema, args.limit, args.repeats)
                artifact = "benchmarks"
        write_artifact(directory, artifact, observations, settings, provenance)
        print(f"{artifact} recorded. Failed/unsupported observations remain in the artifact.")
    return 0


def guarded_execute(args: argparse.Namespace) -> int:
    try:
        return execute(args)
    except SageError as error:
        print(str(error), file=sys.stderr)
    except ValidationError:
        print(
            "Invalid Sage configuration; check timeout (1–300 seconds) and local settings.",
            file=sys.stderr,
        )
    except OSError, ValueError, TypeError, KeyError:
        print(
            "Discovery failed processing metadata/artifacts; no private details emitted.",
            file=sys.stderr,
        )
    return 1


def worker(args: argparse.Namespace) -> None:
    raise SystemExit(guarded_execute(args))


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command in {"report", "drivers"}:
        return guarded_execute(args)
    # One worker owns the only Sage connection. No parallel readers. This bounds a
    # driver that accepts the timeout setting but fails to honor it during reads.
    process = multiprocessing.get_context("spawn").Process(target=worker, args=(args,))
    process.start()
    try:
        process.join(args.deadline_seconds)
        if process.is_alive():
            process.terminate()
            process.join(5)
            if process.is_alive():
                process.kill()
                process.join(5)
            print(
                "Discovery deadline exceeded; worker stopped. Partial artifacts are incomplete.",
                file=sys.stderr,
            )
            return 1
        return 0 if process.exitcode == 0 else 1
    except KeyboardInterrupt:
        process.terminate()
        process.join(5)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
