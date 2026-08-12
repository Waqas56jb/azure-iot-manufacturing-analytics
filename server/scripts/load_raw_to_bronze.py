"""CLI entry: load raw dataset.csv into ADLS Gen2 Bronze via ADF."""

from src.ingestion.adf_loader import load_raw_to_bronze


if __name__ == "__main__":
    run_id = load_raw_to_bronze(wait=True)
    print(f"SUCCESS: Bronze load complete. ADF run_id={run_id}")
