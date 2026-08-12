"""
Build Silver + Gold Delta Lake tables on ADLS Gen2 from Bronze raw CSV.

Mirrors the Databricks Scala notebooks (01_bronze_to_silver / 02_silver_to_gold)
using delta-rs so medallion layers can be produced when cluster capacity is limited.
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
from deltalake import write_deltalake

from src.common.config import load_env
from src.common.logging import get_logger

logger = get_logger(__name__)
SERVER_ROOT = Path(__file__).resolve().parents[2]


def _fs_client(account: str, filesystem: str):
    cred = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    svc = DataLakeServiceClient(f"https://{account}.dfs.core.windows.net", credential=cred)
    return svc.get_file_system_client(filesystem)


def download_bronze_csv(account: str) -> pd.DataFrame:
    fs = _fs_client(account, "bronze")
    file_client = fs.get_file_client("manufacturing/iot/dataset.csv")
    data = file_client.download_file().readall()
    df = pd.read_csv(io.BytesIO(data))
    logger.info("Downloaded Bronze CSV rows=%s cols=%s", len(df), list(df.columns))
    return df


def build_silver(df: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "UDI": "udi",
        "Product ID": "product_id",
        "Type": "product_type",
        "Air temperature [K]": "air_temperature_k",
        "Process temperature [K]": "process_temperature_k",
        "Rotational speed [rpm]": "rotational_speed_rpm",
        "Torque [Nm]": "torque_nm",
        "Tool wear [min]": "tool_wear_min",
        "Machine failure": "machine_failure",
        "TWF": "twf",
        "HDF": "hdf",
        "PWF": "pwf",
        "OSF": "osf",
        "RNF": "rnf",
    }
    # Handle BOM on first column if present
    cols = {c: rename.get(c.lstrip("\ufeff"), c) for c in df.columns}
    s = df.rename(columns=cols)
    for c in rename.values():
        if c not in s.columns and c == "udi" and "UDI" in df.columns:
            pass
    # Normalize udi if BOM key survived
    if "udi" not in s.columns:
        for c in s.columns:
            if c.replace("\ufeff", "") == "udi" or c.endswith("UDI"):
                s = s.rename(columns={c: "udi"})
                break

    s["udi"] = pd.to_numeric(s["udi"], errors="coerce").astype("Int64")
    s["product_id"] = s["product_id"].astype(str)
    s["product_type"] = s["product_type"].astype(str)
    for c in [
        "air_temperature_k",
        "process_temperature_k",
        "rotational_speed_rpm",
        "torque_nm",
        "tool_wear_min",
    ]:
        s[c] = pd.to_numeric(s[c], errors="coerce")
    for c in ["machine_failure", "twf", "hdf", "pwf", "osf", "rnf"]:
        s[c] = pd.to_numeric(s[c], errors="coerce").fillna(0).astype(int)

    s = s[s["udi"].notna()]
    s = s[s["product_type"].isin(["L", "M", "H"])]
    s = s.drop_duplicates(subset=["udi"])
    s["temp_delta_k"] = s["process_temperature_k"] - s["air_temperature_k"]
    s["power_approx_w"] = s["torque_nm"] * s["rotational_speed_rpm"] * (2.0 * np.pi / 60.0)
    s["ingested_at"] = datetime.now(timezone.utc)
    s["source_system"] = "adls_bronze_iot"
    return s.reset_index(drop=True)


def build_gold(silver: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    g = silver.copy()
    g["failure_type"] = np.select(
        [g["twf"] == 1, g["hdf"] == 1, g["pwf"] == 1, g["osf"] == 1, g["rnf"] == 1],
        ["TWF", "HDF", "PWF", "OSF", "RNF"],
        default="NONE",
    )
    g["risk_band"] = np.select(
        [(g["tool_wear_min"] >= 200) | (g["torque_nm"] >= 60), (g["tool_wear_min"] >= 120) | (g["torque_nm"] >= 45)],
        ["HIGH", "MEDIUM"],
        default="LOW",
    )
    g["is_failed"] = g["machine_failure"] == 1
    g["gold_built_at"] = datetime.now(timezone.utc)
    features = g[
        [
            "udi",
            "product_id",
            "product_type",
            "air_temperature_k",
            "process_temperature_k",
            "temp_delta_k",
            "rotational_speed_rpm",
            "torque_nm",
            "power_approx_w",
            "tool_wear_min",
            "machine_failure",
            "is_failed",
            "failure_type",
            "risk_band",
            "twf",
            "hdf",
            "pwf",
            "osf",
            "rnf",
            "gold_built_at",
        ]
    ].copy()

    summary = (
        silver.groupby("product_type", as_index=False)
        .agg(
            total_records=("udi", "count"),
            failure_count=("machine_failure", "sum"),
            failure_rate=("machine_failure", "mean"),
            avg_air_temp_k=("air_temperature_k", "mean"),
            avg_process_temp_k=("process_temperature_k", "mean"),
            avg_rpm=("rotational_speed_rpm", "mean"),
            avg_torque_nm=("torque_nm", "mean"),
            avg_tool_wear_min=("tool_wear_min", "mean"),
            twf_count=("twf", "sum"),
            hdf_count=("hdf", "sum"),
            pwf_count=("pwf", "sum"),
            osf_count=("osf", "sum"),
            rnf_count=("rnf", "sum"),
        )
        .round(4)
    )
    summary["gold_built_at"] = datetime.now(timezone.utc)
    return features, summary


def _storage_options(account: str) -> dict:
    # Prefer account key from env for delta-rs Azure writer; fall back to Azure CLI credential chain via AZURE_STORAGE_ACCOUNT
    key = os.getenv("ADLS_ACCOUNT_KEY")
    opts = {"account_name": account}
    if key:
        opts["account_key"] = key
    else:
        # delta-rs can use azure cli / env creds with this flag set
        opts["use_azure_cli"] = "true"
    return opts


def write_delta(df: pd.DataFrame, account: str, filesystem: str, path: str) -> str:
    uri = f"abfss://{filesystem}@{account}.dfs.core.windows.net/{path}"
    logger.info("Writing Delta table -> %s rows=%s", uri, len(df))
    write_deltalake(
        uri,
        df,
        mode="overwrite",
        schema_mode="overwrite",
        storage_options=_storage_options(account),
    )
    return uri


def run_medallion() -> dict:
    load_env()
    account = os.environ["ADLS_ACCOUNT_NAME"]
    bronze = download_bronze_csv(account)
    silver = build_silver(bronze)
    gold_features, gold_summary = build_gold(silver)

    silver_uri = write_delta(silver, account, "silver", "manufacturing/iot/telemetry")
    gold_feat_uri = write_delta(gold_features, account, "gold", "manufacturing/iot/telemetry_features")
    gold_sum_uri = write_delta(gold_summary, account, "gold", "manufacturing/iot/failure_summary_by_type")

    result = {
        "silver_rows": len(silver),
        "gold_feature_rows": len(gold_features),
        "gold_summary_rows": len(gold_summary),
        "silver_uri": silver_uri,
        "gold_features_uri": gold_feat_uri,
        "gold_summary_uri": gold_sum_uri,
    }
    logger.info("Medallion complete: %s", result)
    return result


if __name__ == "__main__":
    out = run_medallion()
    print("SUCCESS Silver/Gold Delta ready:")
    for k, v in out.items():
        print(f"  {k}={v}")
