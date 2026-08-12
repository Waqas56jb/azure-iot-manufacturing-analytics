"""CLI helper: trigger Databricks Scala medallion job (Bronze->Silver->Gold)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

from azure.identity import DefaultAzureCredential


DATABRICKS_AAD_RESOURCE = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"


def aad_token() -> str:
    # Prefer az CLI for reliability in local lab setups
    out = subprocess.check_output(
        [
            "az",
            "account",
            "get-access-token",
            "--resource",
            DATABRICKS_AAD_RESOURCE,
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ],
        text=True,
    ).strip()
    return out


def main() -> int:
    host = os.environ.get("DATABRICKS_HOST", "https://adb-7405610081329680.0.azuredatabricks.net")
    job_id = int(os.environ.get("DATABRICKS_JOB_ID", "121911173786629"))
    token = aad_token()
    env = os.environ.copy()
    env["DATABRICKS_HOST"] = host
    env["DATABRICKS_TOKEN"] = token

    run = subprocess.check_output(
        ["databricks", "jobs", "run-now", "--json", json.dumps({"job_id": job_id}), "-o", "json"],
        env=env,
        text=True,
    )
    run_id = json.loads(run)["run_id"]
    print(f"Started Databricks job_id={job_id} run_id={run_id}")

    while True:
        info = json.loads(
            subprocess.check_output(
                ["databricks", "jobs", "get-run", str(run_id), "-o", "json"],
                env=env,
                text=True,
            )
        )
        state = info["state"]["life_cycle_state"]
        result = info["state"].get("result_state")
        print(f"state={state} result={result}")
        if state not in {"PENDING", "RUNNING", "TERMINATING", "QUEUED", "WAITING_FOR_RETRY"}:
            print(info["state"].get("state_message", ""))
            return 0 if result == "SUCCESS" else 1
        time.sleep(30)


if __name__ == "__main__":
    sys.exit(main())
