"""
Airflow DAG: Manufacturing IoT medallion + MLOps orchestration.

Pipeline stages (placeholders):
  1) Ingest raw CSV / IoT → ADLS
  2) ADF copy → Bronze
  3) Databricks Bronze → Silver → Gold
  4) Synapse star schema load
  5) ML train / score
  6) Publish metrics for Power BI
"""

from datetime import datetime, timedelta

# from airflow import DAG
# from airflow.operators.python import PythonOperator

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": True,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# dag = DAG(
#     dag_id="manufacturing_iot_mlops",
#     default_args=default_args,
#     description="IoT → ADF → ADLS medallion → Synapse → ML → Power BI",
#     schedule_interval="@daily",
#     start_date=datetime(2026, 1, 1),
#     catchup=False,
#     tags=["manufacturing", "iot", "mlops"],
# )
