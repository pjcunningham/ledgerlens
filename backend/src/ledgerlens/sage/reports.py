"""Local JSON artifacts and an allowlisted, deliberately lossy public report."""

import json
import re
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from ledgerlens.sage.config import SageError, SageSettings
from ledgerlens.sage.models import LINKS, PRIORITY_TABLES, Json

ARTIFACTS = ("environment", "schema", "capabilities", "profile", "relationships", "benchmarks")
OPERATIONS = {
    "simple_select",
    "projection",
    "where_equality",
    "where_range",
    "order_by",
    "count",
    "distinct",
    "and_or",
    "parameters",
    "null_predicate",
    "top",
    "limit",
    "offset",
    "date_parameters",
    "string_parameters",
    "case_comparison",
    "aggregate",
    "inner_join",
    "left_join",
    "metadata_enumeration",
    "sequential_read",
    "filtered_lookup",
}


def json_value(value: object) -> Json:
    def default(item: object) -> object:
        if is_dataclass(item) and not isinstance(item, type):
            return asdict(item)
        raise TypeError("Non-artifact type cannot be serialized")

    return cast(Json, json.loads(json.dumps(value, default=default, allow_nan=False)))


# These values are structural, supplied by controlled builders or metadata APIs.
# Never substring-redact them: even a one-character credential may overlap them.
STRUCTURAL_FIELDS = {
    "name",
    "operation",
    "status",
    "sqlstate",
    "kind",
    "type_name",
    "python_types",
    "fingerprint",
    "git_commit",
    "timestamp",
    "ledgerlens",
    "python",
    "pyodbc",
    "sage_application_version",
    "sage_build",
    "sage_data_version",
    "driver_version",
    "driver_name",
    "drivers",
    "odbc_version",
    "dbms_name",
    "dbms_version",
    "os",
    "os_version",
    "column_name",
    "pktable_name",
    "pkcolumn_name",
    "fktable_name",
    "fkcolumn_name",
    "asc_or_desc",
    "left_table",
    "left_column",
    "right_table",
    "right_column",
    "table",
    "potential_change_fields",
    "fetch_method",
    "observed_cardinality",
    "scope",
    "comparison",
    "interpretation",
    "sentinel_interpretation",
    "earliest_date",
    "latest_date",
    "connection",
    "read_access",
    "query_timeout",
    "reason",
    "row_count_state",
    "row_count_status",
    "command",
    "run_id",
    "selected_tables",
    "completion",
}


def redact(value: Json, settings: SageSettings, *, field: str = "") -> Json:
    """Omit potentially sensitive text by field; preserve structure regardless of secrets.

    Unknown text is omitted completely, including paths and identifiers not known
    to settings. Settings remains an argument for existing artifact callers.
    """
    if isinstance(value, str):
        return value if field in STRUCTURAL_FIELDS else "[redacted]"
    if isinstance(value, list):
        return [redact(item, settings, field=field) for item in value]
    if isinstance(value, dict):
        return {key: redact(item, settings, field=key) for key, item in value.items()}
    return value


def write_provenance(directory: Path, name: str, provenance: dict[str, Json]) -> None:
    if name not in (*ARTIFACTS, "report"):
        raise SageError("Unknown artifact name.")
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / f"{name}.provenance.json.tmp"
    temporary.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(directory / f"{name}.provenance.json")


def write_artifact(
    directory: Path,
    name: str,
    value: object,
    settings: SageSettings,
    provenance: dict[str, Json] | None = None,
) -> None:
    if name not in ARTIFACTS:
        raise SageError("Unknown artifact name.")
    directory.mkdir(parents=True, exist_ok=True)
    payload = redact(json_value(value), settings)
    temporary = directory / f"{name}.json.tmp"
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(directory / f"{name}.json")
    if provenance is not None:
        write_provenance(directory, name, provenance)


def load_artifacts(directory: Path) -> dict[str, Json]:
    result: dict[str, Json] = {}
    for name in ARTIFACTS:
        path = directory / f"{name}.json"
        if path.exists():
            if path.stat().st_size > 20_000_000:
                raise SageError("Artifact exceeds report size limit.")
            result[name] = cast(Json, json.loads(path.read_text(encoding="utf-8")))
        provenance = directory / f"{name}.provenance.json"
        if provenance.exists():
            result[f"{name}_provenance"] = cast(
                Json, json.loads(provenance.read_text(encoding="utf-8"))
            )
    if not result:
        raise SageError("No discovery artifacts found; run discovery first.")
    return result


def mapping(value: Json) -> dict[str, Json]:
    return value if isinstance(value, dict) else {}


def records(value: Json) -> list[dict[str, Json]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def sanitized_report(artifacts: dict[str, Json]) -> str:
    lines = [
        "# Sage discovery report (sanitized)",
        "",
        "Metadata, observations, and interpretations are separate. Missing evidence is unknown.",
        "Company-specific strings, raw keys, schema dumps, and free text are excluded.",
        "",
        "## Environment fingerprint",
        "",
    ]
    env = mapping(artifacts.get("environment"))
    for name in (
        "ledgerlens",
        "python",
        "pyodbc",
        "sage_application_version",
        "sage_build",
        "sage_data_version",
        "driver_version",
        "odbc_version",
    ):
        value = env.get(name)
        match = (
            re.match(r"^([0-9]+(?:\.[0-9]+){0,5})(?:\s|$)", value)
            if isinstance(value, str)
            else None
        )
        safe = match.group(1) if match else "unknown / omitted"
        lines.append(f"- {name}: {safe}")
    lines.extend(
        [
            "",
            "## Artifact provenance",
            "",
            "Separate commands are separate observations, not one consistent snapshot.",
        ]
    )
    for name in ARTIFACTS:
        provenance = mapping(artifacts.get(f"{name}_provenance"))
        if not provenance:
            lines.append(f"- {name}: provenance unavailable (legacy or absent artifact)")
            continue
        completion = provenance.get("completion")
        command = provenance.get("command")
        if completion not in {"in-progress", "partial", "complete"} or command not in {
            "probe",
            "schema",
            "describe-table",
            "capabilities",
            "profile",
            "relationships",
            "benchmark",
        }:
            continue
        lines.append(f"- {name}: command={command}; completion={completion}")
        timestamp = provenance.get("timestamp")
        if isinstance(timestamp, str) and re.fullmatch(r"[0-9T:.+Z-]{19,40}", timestamp):
            lines.append(f"  - timestamp: {timestamp}")
        for key in ("sample_limit", "repeats", "deadline_seconds"):
            value = provenance.get(key)
            if type(value) is int:
                lines.append(f"  - {key}: {value}")
        selected = provenance.get("selected_tables")
        if isinstance(selected, list):
            safe_tables = [name for name in PRIORITY_TABLES if name in selected]
            lines.append("  - selected priority tables: " + ", ".join(safe_tables))
    schema = mapping(artifacts.get("schema"))
    tables = records(schema.get("tables"))
    lines.extend(
        [
            "",
            "## Schema overview",
            "",
            f"Tables/views recorded: {len(tables)}.",
            "Declared PK/FK/index metadata is not proof of uniqueness or referential integrity.",
            "",
            "## Priority tables",
            "",
        ]
    )
    names = {table.get("name") for table in tables if isinstance(table.get("name"), str)}
    lines.extend(
        f"- {name}: {'present' if name in names else 'not recorded'}" for name in PRIORITY_TABLES
    )
    for title, source in (
        ("SQL capability matrix / Driver capabilities", "capabilities"),
        ("Potential identifiers / Data-type observations", "profile"),
        ("Published relationships tested / Observed cardinalities", "relationships"),
        ("Performance observations", "benchmarks"),
    ):
        lines.extend(["", f"## {title}", ""])
        observations = records(artifacts.get(source))
        allowed = (
            OPERATIONS
            | set(PRIORITY_TABLES)
            | {
                f"{link.left_table}.{link.left_column}->{link.right_table}.{link.right_column}"
                for link in LINKS
            }
        )
        for observation in observations:
            operation = observation.get("operation")
            status = observation.get("status")
            if not isinstance(operation, str) or not isinstance(status, str):
                continue
            if operation not in allowed or status not in {
                "supported",
                "unsupported",
                "failed",
                "not-tested",
            }:
                continue
            details = mapping(observation.get("details"))
            outcomes = [key for key in ("count", "sample") if isinstance(details.get(key), dict)]
            lines.append(f"- {operation}" if outcomes else f"- {operation}: {status}")
            for key in outcomes:
                outcome = mapping(details.get(key))
                outcome_status = outcome.get("status")
                if outcome_status not in {"supported", "unsupported", "failed", "not-tested"}:
                    continue
                lines.append(f"  - {key}: {outcome_status}")
                outcome_state = outcome.get("sqlstate")
                if isinstance(outcome_state, str) and re.fullmatch(r"[A-Z0-9]{5}", outcome_state):
                    lines.append(f"    - SQLSTATE: {outcome_state}")
                count = outcome.get("row_count")
                if type(count) is int:
                    lines.append(f"    - row_count: {count}")
            state = observation.get("sqlstate")
            if isinstance(state, str) and re.fullmatch(r"[A-Z0-9]{5}", state):
                lines.append(f"  - SQLSTATE: {state}")
            details = mapping(observation.get("details"))
            for key in (
                "row_count",
                "fetched_count",
                "elapsed_seconds",
                "rows_per_second",
                "batch_size",
                "left_distinct",
                "right_distinct",
                "matched_left_rows",
                "orphan_count",
                "both_reads_complete",
            ):
                value = details.get(key)
                if type(value) in (int, float, bool):
                    lines.append(f"  - {key}: {value}")
            cardinality = details.get("observed_cardinality")
            if cardinality in {
                "one-to-one",
                "one-to-many",
                "many-to-one",
                "potentially-many-to-many",
                "no-matches",
            }:
                lines.append(f"  - observed cardinality: {cardinality}")
            columns = mapping(details.get("columns"))
            types: set[str] = set()
            for column in columns.values():
                values = mapping(column).get("python_types")
                if isinstance(values, list):
                    types.update(value for value in values if isinstance(value, str))
            safe_types = sorted(
                types
                & {
                    "str",
                    "int",
                    "float",
                    "Decimal",
                    "date",
                    "datetime",
                    "bool",
                    "bytes",
                    "NoneType",
                    "other",
                }
            )
            if safe_types:
                lines.append("  - Python types observed: " + ", ".join(safe_types))
        if not observations:
            lines.append("Not evaluated.")
    lines.extend(
        [
            "",
            "## Risks / unknowns",
            "",
            "Samples cannot establish global uniqueness, orphan absence, or deletion semantics.",
            "SQL success alone does not prove semantic correctness or timeout enforcement.",
            "Sage desktop cross-checks and exact application/build identification are necessary.",
            "",
            "## Recommendations for Phase 003",
            "",
            "Verify evidence before selecting canonical identifiers and date/money rules.",
            "Do not infer incremental synchronization support from field names or one benchmark.",
            "",
        ]
    )
    return "\n".join(lines)


def report(directory: Path, *, sanitized: bool = True) -> str:
    artifacts = load_artifacts(directory)
    if sanitized:
        content = sanitized_report(artifacts)
    else:
        content = (
            "# Local Sage discovery (not for committing)\n\n```json\n"
            + json.dumps(artifacts, indent=2, sort_keys=True)
            + "\n```\n"
        )
    (directory / "report.md").write_text(content, encoding="utf-8")
    write_provenance(
        directory,
        "report",
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "command": "report",
            "completion": "complete",
            "sanitized": sanitized,
            "sources": {name: artifacts.get(f"{name}_provenance") for name in ARTIFACTS},
        },
    )
    return content
