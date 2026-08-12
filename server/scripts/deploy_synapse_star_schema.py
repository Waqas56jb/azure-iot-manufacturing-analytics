"""Deploy star-schema SQL to Synapse serverless and verify row counts."""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

import pyodbc

SERVER_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = SERVER_ROOT / "sql" / "star_schema"


def _pick_driver() -> str:
    drivers = [d for d in pyodbc.drivers()]
    for preferred in (
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server",
    ):
        if preferred in drivers:
            return preferred
    raise RuntimeError(f"No SQL Server ODBC driver found. Installed: {drivers}")


def _conn_str(database: str = "master") -> str:
    host = os.environ.get(
        "SYNAPSE_SQL_ENDPOINT",
        "syn-iot-mfg-wus2-ondemand.sql.azuresynapse.net",
    )
    user = os.environ.get("SYNAPSE_SQL_USER", "sqladminuser")
    password = os.environ["SYNAPSE_SQL_PASSWORD"]
    driver = _pick_driver()
    return (
        f"Driver={{{driver}}};"
        f"Server=tcp:{host},1433;"
        f"Database={database};"
        f"Uid={user};"
        f"Pwd={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=60;"
    )


def _split_batches(sql_text: str) -> list[str]:
    parts = re.split(r"^\s*GO\s*$", sql_text, flags=re.IGNORECASE | re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def execute_script(path: Path, database: str = "master") -> None:
    print(f"Running {path.name} on database={database}")
    batches = _split_batches(path.read_text(encoding="utf-8"))
    # First script creates DB from master; later scripts use manufacturing_dw
    conn = pyodbc.connect(_conn_str(database), autocommit=True)
    cur = conn.cursor()
    for i, batch in enumerate(batches, 1):
        # Skip USE statements handled by connection database when possible
        try:
            cur.execute(batch)
            while cur.nextset():
                pass
            print(f"  batch {i}/{len(batches)} OK")
        except pyodbc.Error as exc:
            msg = str(exc)
            # idempotent skips
            if "already an object named" in msg or "already exists" in msg.lower():
                print(f"  batch {i}/{len(batches)} skipped (exists)")
                continue
            raise
    cur.close()
    conn.close()


def verify() -> None:
    conn = pyodbc.connect(_conn_str("manufacturing_dw"), autocommit=True)
    cur = conn.cursor()
    tables = [
        "dim_product",
        "dim_failure_type",
        "dim_risk_band",
        "dim_date",
        "fact_machine_telemetry",
    ]
    print("Verification counts:")
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM dbo.{t}")
        count = cur.fetchone()[0]
        print(f"  {t}={count}")

    cur.execute(
        """
        SELECT TOP 5
            p.product_type,
            ft.failure_type_code,
            rb.risk_band_code,
            f.machine_failure,
            f.tool_wear_min,
            f.torque_nm
        FROM dbo.fact_machine_telemetry f
        JOIN dbo.dim_product p ON f.product_key = p.product_key
        JOIN dbo.dim_failure_type ft ON f.failure_type_key = ft.failure_type_key
        JOIN dbo.dim_risk_band rb ON f.risk_band_key = rb.risk_band_key
        WHERE f.machine_failure = 1
        ORDER BY f.tool_wear_min DESC
        """
    )
    rows = cur.fetchall()
    print("Sample failed rows:")
    for r in rows:
        print(" ", tuple(r))
    cur.close()
    conn.close()


def main() -> None:
    pwd_file = SERVER_ROOT / ".synapse_sql_password.tmp"
    if pwd_file.exists() and not os.getenv("SYNAPSE_SQL_PASSWORD"):
        os.environ["SYNAPSE_SQL_PASSWORD"] = pwd_file.read_text(encoding="utf-8").strip()
    if not os.getenv("SYNAPSE_SQL_PASSWORD"):
        raise SystemExit("SYNAPSE_SQL_PASSWORD missing")

    # Wait briefly for SQL endpoint readiness
    for attempt in range(1, 9):
        try:
            conn = pyodbc.connect(_conn_str("master"), autocommit=True)
            conn.close()
            print("Synapse SQL endpoint reachable")
            break
        except Exception as exc:
            print(f"Waiting for SQL endpoint ({attempt}/8): {exc}")
            time.sleep(20)
    else:
        raise SystemExit("Synapse SQL endpoint not reachable")

    execute_script(SQL_DIR / "001_create_dimensions.sql", database="master")
    execute_script(SQL_DIR / "002_create_views.sql", database="manufacturing_dw")
    verify()
    print("SUCCESS Synapse star schema deployed")


if __name__ == "__main__":
    main()
