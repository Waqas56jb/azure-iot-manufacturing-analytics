"""
Build Synapse star-schema marts (Parquet) on ADLS Gold from Gold Delta features.
"""

from __future__ import annotations

import io
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient
from deltalake import DeltaTable

from src.common.config import load_env
from src.common.logging import get_logger

logger = get_logger(__name__)


FAILURE_DIM = pd.DataFrame(
    [
        {"failure_type_key": 0, "failure_type_code": "NONE", "failure_type_name": "No Failure"},
        {"failure_type_key": 1, "failure_type_code": "TWF", "failure_type_name": "Tool Wear Failure"},
        {"failure_type_key": 2, "failure_type_code": "HDF", "failure_type_name": "Heat Dissipation Failure"},
        {"failure_type_key": 3, "failure_type_code": "PWF", "failure_type_name": "Power Failure"},
        {"failure_type_key": 4, "failure_type_code": "OSF", "failure_type_name": "Overstrain Failure"},
        {"failure_type_key": 5, "failure_type_code": "RNF", "failure_type_name": "Random Failure"},
    ]
)

RISK_DIM = pd.DataFrame(
    [
        {"risk_band_key": 1, "risk_band_code": "LOW", "risk_band_name": "Low Risk"},
        {"risk_band_key": 2, "risk_band_code": "MEDIUM", "risk_band_name": "Medium Risk"},
        {"risk_band_key": 3, "risk_band_code": "HIGH", "risk_band_name": "High Risk"},
    ]
)

TYPE_NAME = {"L": "Low Quality", "M": "Medium Quality", "H": "High Quality"}


def _storage_options(account: str) -> dict:
    opts = {"account_name": account}
    key = os.getenv("ADLS_ACCOUNT_KEY")
    if key:
        opts["account_key"] = key
    else:
        opts["use_azure_cli"] = "true"
    return opts


def _datalake(account: str) -> DataLakeServiceClient:
    cred = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    return DataLakeServiceClient(f"https://{account}.dfs.core.windows.net", credential=cred)


def _upload_parquet(account: str, filesystem: str, directory: str, df: pd.DataFrame, file_name: str) -> None:
    svc = _datalake(account)
    fs = svc.get_file_system_client(filesystem)
    try:
        fs.create_file_system()
    except Exception:
        pass
    dir_client = fs.get_directory_client(directory)
    try:
        dir_client.create_directory()
    except Exception:
        pass

    # overwrite directory contents for idempotent loads
    try:
        for path in fs.get_paths(path=directory):
            if not path.is_directory:
                fs.get_file_client(path.name).delete_file()
    except Exception:
        pass

    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow")
    data = buf.getvalue()
    file_client = dir_client.get_file_client(file_name)
    file_client.upload_data(data, overwrite=True, length=len(data))
    logger.info("Uploaded %s/%s/%s rows=%s bytes=%s", filesystem, directory, file_name, len(df), len(data))


def load_gold_features(account: str) -> pd.DataFrame:
    uri = f"abfss://gold@{account}.dfs.core.windows.net/manufacturing/iot/telemetry_features"
    dt = DeltaTable(uri, storage_options=_storage_options(account))
    df = dt.to_pandas()
    logger.info("Loaded gold features rows=%s", len(df))
    return df


def build_star(gold: pd.DataFrame) -> dict[str, pd.DataFrame]:
    products = (
        gold[["product_id", "product_type"]]
        .drop_duplicates()
        .sort_values(["product_type", "product_id"])
        .reset_index(drop=True)
    )
    products.insert(0, "product_key", products.index + 1)
    products["product_type_name"] = products["product_type"].map(TYPE_NAME).fillna("Unknown")

    # Date dimension from gold_built_at (fallback: today UTC)
    if "gold_built_at" in gold.columns:
        dates = pd.to_datetime(gold["gold_built_at"], utc=True, errors="coerce")
    else:
        dates = pd.Series([pd.Timestamp.now(tz="UTC")] * len(gold))
    gold = gold.copy()
    gold["_full_date"] = dates.dt.date
    gold["_full_date"] = gold["_full_date"].fillna(datetime.now(timezone.utc).date())

    unique_dates = sorted(set(gold["_full_date"]))
    dim_date = pd.DataFrame({"full_date": unique_dates})
    dim_date["full_date"] = pd.to_datetime(dim_date["full_date"])
    dim_date["date_key"] = dim_date["full_date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["year"] = dim_date["full_date"].dt.year
    dim_date["month"] = dim_date["full_date"].dt.month
    dim_date["day"] = dim_date["full_date"].dt.day
    dim_date["month_name"] = dim_date["full_date"].dt.month_name()
    dim_date["day_name"] = dim_date["full_date"].dt.day_name()
    dim_date["full_date"] = dim_date["full_date"].dt.date

    fail_map = dict(zip(FAILURE_DIM["failure_type_code"], FAILURE_DIM["failure_type_key"]))
    risk_map = dict(zip(RISK_DIM["risk_band_code"], RISK_DIM["risk_band_key"]))
    prod_map = dict(zip(products["product_id"], products["product_key"]))
    date_map = dict(zip(dim_date["full_date"], dim_date["date_key"]))

    fact = pd.DataFrame(
        {
            "telemetry_key": gold["udi"].astype("int64"),
            "udi": gold["udi"].astype("int64"),
            "product_key": gold["product_id"].map(prod_map).astype("int64"),
            "failure_type_key": gold["failure_type"].map(fail_map).fillna(0).astype("int64"),
            "risk_band_key": gold["risk_band"].map(risk_map).fillna(1).astype("int64"),
            "date_key": gold["_full_date"].map(date_map).astype("int64"),
            "air_temperature_k": gold["air_temperature_k"].astype(float),
            "process_temperature_k": gold["process_temperature_k"].astype(float),
            "temp_delta_k": gold["temp_delta_k"].astype(float),
            "rotational_speed_rpm": gold["rotational_speed_rpm"].astype(float),
            "torque_nm": gold["torque_nm"].astype(float),
            "power_approx_w": gold["power_approx_w"].astype(float),
            "tool_wear_min": gold["tool_wear_min"].astype(float),
            "machine_failure": gold["machine_failure"].astype("int64"),
            "is_failed": gold["is_failed"].astype(bool),
            "twf": gold["twf"].astype("int64"),
            "hdf": gold["hdf"].astype("int64"),
            "pwf": gold["pwf"].astype("int64"),
            "osf": gold["osf"].astype("int64"),
            "rnf": gold["rnf"].astype("int64"),
        }
    )

    return {
        "dim_product": products,
        "dim_failure_type": FAILURE_DIM,
        "dim_risk_band": RISK_DIM,
        "dim_date": dim_date,
        "fact_machine_telemetry": fact,
    }


def publish_star_schema() -> dict:
    load_env()
    account = os.environ["ADLS_ACCOUNT_NAME"]
    if not os.getenv("ADLS_ACCOUNT_KEY"):
        # fetch via az if available
        import subprocess

        key = subprocess.check_output(
            [
                "az",
                "storage",
                "account",
                "keys",
                "list",
                "--account-name",
                account,
                "--resource-group",
                os.environ.get("AZURE_RESOURCE_GROUP", "rg-iot-manufacturing-analytics"),
                "--query",
                "[0].value",
                "-o",
                "tsv",
            ],
            text=True,
        ).strip()
        os.environ["ADLS_ACCOUNT_KEY"] = key

    gold = load_gold_features(account)
    tables = build_star(gold)
    base = "marts/star_schema"
    for name, df in tables.items():
        _upload_parquet(account, "gold", f"{base}/{name}", df, f"{name}.parquet")

    summary = {name: len(df) for name, df in tables.items()}
    logger.info("Star schema published: %s", summary)
    return summary


if __name__ == "__main__":
    out = publish_star_schema()
    print("SUCCESS star schema marts published:")
    for k, v in out.items():
        print(f"  {k}={v}")
