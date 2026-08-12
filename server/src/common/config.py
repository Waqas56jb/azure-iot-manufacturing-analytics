from pathlib import Path

import yaml
from dotenv import load_dotenv


def load_env(env_path: str | None = None) -> None:
    """Load environment variables from .env."""
    root = Path(__file__).resolve().parents[2]
    load_dotenv(env_path or root / ".env")


def load_yaml(path: str | Path) -> dict:
    """Load a YAML config file."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
