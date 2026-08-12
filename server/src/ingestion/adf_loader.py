"""
Load all raw manufacturing IoT data into ADLS Gen2 Bronze via Azure Data Factory.

Flow:
  1) Python uploads raw CSV → ADLS `landing/raw/manufacturing/iot/`
  2) Python triggers ADF pipeline `pl_ingest_manufacturing_iot`
  3) ADF Copy activity writes → ADLS `bronze/manufacturing/iot/`
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.mgmt.datafactory.models import CreateRunResponse
from azure.storage.filedatalake import DataLakeServiceClient

from src.common.config import load_env
from src.common.logging import get_logger

logger = get_logger(__name__)

SERVER_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_FILE = SERVER_ROOT / "data" / "raw" / "dataset.csv"


def _require_env(*keys: str) -> dict[str, str]:
    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")
    return {k: os.environ[k] for k in keys}


def get_datalake_service_client() -> DataLakeServiceClient:
    """ADLS Gen2 client using Azure CLI / VS Code / Managed Identity credentials."""
    account = os.environ["ADLS_ACCOUNT_NAME"]
    account_url = f"https://{account}.dfs.core.windows.net"
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    return DataLakeServiceClient(account_url, credential=credential)


def upload_raw_to_landing(
    local_file: Path = DEFAULT_RAW_FILE,
    landing_filesystem: str = "landing",
    landing_dir: str = "raw/manufacturing/iot",
) -> str:
    """Upload the full raw CSV into ADLS landing zone (ADF source)."""
    if not local_file.exists():
        raise FileNotFoundError(f"Raw file not found: {local_file}")

    file_name = local_file.name
    remote_path = f"{landing_dir}/{file_name}"

    service = get_datalake_service_client()
    fs = service.get_file_system_client(landing_filesystem)
    try:
        fs.create_file_system()
    except Exception:
        pass

    directory = fs.get_directory_client(landing_dir)
    try:
        directory.create_directory()
    except Exception:
        pass

    file_client = directory.get_file_client(file_name)
    file_size = local_file.stat().st_size
    logger.info("Uploading %s (%s bytes) -> %s/%s", local_file, file_size, landing_filesystem, remote_path)

    with open(local_file, "rb") as f:
        file_client.upload_data(f, overwrite=True, length=file_size)

    logger.info("Landing upload complete: abfss://%s@%s.dfs.core.windows.net/%s", landing_filesystem, os.environ["ADLS_ACCOUNT_NAME"], remote_path)
    return remote_path


def get_adf_client() -> DataFactoryManagementClient:
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    return DataFactoryManagementClient(credential, subscription_id)


def trigger_adf_pipeline(
    pipeline_name: str | None = None,
    parameters: dict | None = None,
) -> str:
    """Create an ADF pipeline run and return the run ID."""
    env = _require_env("AZURE_RESOURCE_GROUP", "ADF_FACTORY_NAME")
    pipeline_name = pipeline_name or os.getenv("ADF_PIPELINE_NAME", "pl_ingest_manufacturing_iot")
    client = get_adf_client()

    logger.info(
        "Triggering ADF pipeline %s on factory %s",
        pipeline_name,
        env["ADF_FACTORY_NAME"],
    )
    response: CreateRunResponse = client.pipelines.create_run(
        resource_group_name=env["AZURE_RESOURCE_GROUP"],
        factory_name=env["ADF_FACTORY_NAME"],
        pipeline_name=pipeline_name,
        parameters=parameters or {},
    )
    run_id = response.run_id
    logger.info("ADF run started: %s", run_id)
    return run_id


def wait_for_pipeline_run(run_id: str, timeout_seconds: int = 600, poll_seconds: int = 10) -> str:
    """Poll ADF until Succeeded/Failed/Cancelled."""
    env = _require_env("AZURE_RESOURCE_GROUP", "ADF_FACTORY_NAME")
    client = get_adf_client()
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        run = client.pipeline_runs.get(
            env["AZURE_RESOURCE_GROUP"],
            env["ADF_FACTORY_NAME"],
            run_id,
        )
        status = run.status
        logger.info("ADF run %s status: %s", run_id, status)
        if status in {"Succeeded", "Failed", "Cancelled"}:
            if status != "Succeeded":
                raise RuntimeError(f"ADF pipeline run {run_id} ended with status={status}: {run.message}")
            return status
        time.sleep(poll_seconds)

    raise TimeoutError(f"ADF run {run_id} did not finish within {timeout_seconds}s")


def verify_bronze_file(
    bronze_filesystem: str | None = None,
    bronze_path: str = "manufacturing/iot/dataset.csv",
) -> bool:
    """Return True if the raw file exists in Bronze."""
    bronze_filesystem = bronze_filesystem or os.getenv("ADLS_FILESYSTEM_BRONZE", "bronze")
    service = get_datalake_service_client()
    fs = service.get_file_system_client(bronze_filesystem)
    file_client = fs.get_file_client(bronze_path)
    props = file_client.get_file_properties()
    logger.info(
        "Bronze file OK: %s/%s size=%s bytes",
        bronze_filesystem,
        bronze_path,
        props.size,
    )
    return True


def load_raw_to_bronze(local_file: Path | None = None, wait: bool = True) -> str:
    """
    End-to-end: upload raw dataset to landing, trigger ADF copy into Bronze.
    Returns ADF run ID.
    """
    load_env()
    _require_env(
        "AZURE_SUBSCRIPTION_ID",
        "AZURE_RESOURCE_GROUP",
        "ADLS_ACCOUNT_NAME",
        "ADF_FACTORY_NAME",
    )

    path = Path(local_file) if local_file else DEFAULT_RAW_FILE
    upload_raw_to_landing(path)
    run_id = trigger_adf_pipeline()
    if wait:
        wait_for_pipeline_run(run_id)
        verify_bronze_file()
    return run_id


if __name__ == "__main__":
    rid = load_raw_to_bronze()
    print(f"Raw data loaded to Bronze via ADF. run_id={rid}")
