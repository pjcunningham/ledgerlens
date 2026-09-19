import platform
import re
import struct
import subprocess
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from ledgerlens.sage.config import SageError
from ledgerlens.sage.connection import Connection, Driver, cursor, load_driver
from ledgerlens.sage.models import Json


def environment(driver: Driver, manual: dict[str, str] | None = None) -> dict[str, Json]:
    commit: str | None = None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[4],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40,64}\s*", result.stdout):
            commit = result.stdout.strip()
    except OSError, subprocess.TimeoutExpired:
        commit = None  # Installed wheels need not have Git available.
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "ledgerlens": version("ledgerlens"),
        "git_commit": commit,
        "os": platform.system(),
        "os_version": platform.version(),
        "python": platform.python_version(),
        "architecture_bits": struct.calcsize("P") * 8,
        "pyodbc": driver.version,
        "sage_application_version": (manual or {}).get("sage_version"),
        "sage_build": (manual or {}).get("sage_build"),
        "sage_data_version": (manual or {}).get("sage_data_version"),
    }


def drivers() -> dict[str, Json]:
    driver = load_driver()
    try:
        installed = sorted(driver.drivers())
    except Exception:
        raise SageError("ODBC driver enumeration failed.") from None
    result = environment(driver)
    result["drivers"] = list(installed)
    result["sage_driver_present"] = any("sage" in name.lower() for name in installed)
    return result


def probe(connection: Connection) -> dict[str, Json]:
    # SQLGetInfo constants, standardized by ODBC. No database/server/path info requested.
    result: dict[str, Json] = {"dsn": "configured", "connection": "OK"}
    for name, code in (
        ("driver_name", 6),
        ("driver_version", 7),
        ("odbc_version", 10),
        ("dbms_name", 17),
        ("dbms_version", 18),
    ):
        try:
            value = connection.getinfo(code)
            result[name] = str(value)
        except Exception:
            result[name] = "unavailable"
    with cursor(connection) as handle:
        handle.tables()
        handle.fetchone()
    result["read_access"] = "OK"
    result["query_timeout_seconds_reported"] = connection.timeout
    result["query_timeout"] = (
        "not configured by driver; process deadline required"
        if connection.timeout == 0
        else "configured; actual driver enforcement requires live verification"
    )
    return result
