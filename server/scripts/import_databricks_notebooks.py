#!/usr/bin/env python3
"""Convert Scala notebook source files into Databricks .ipynb format and import via CLI."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "azure" / "databricks" / "notebooks"
WORKSPACE_DIR = "/Workspace/Shared/manufacturing"


def scala_source_to_ipynb(scala_path: Path) -> dict:
    text = scala_path.read_text(encoding="utf-8")
    # Strip Databricks export header line if present
    text = re.sub(r"^// Databricks notebook source\n", "", text)
    parts = re.split(r"\n// COMMAND ----------\n", text)
    cells = []
    for part in parts:
        part = part.strip("\n")
        if not part.strip():
            continue
        if part.lstrip().startswith("// MAGIC %md"):
            md = []
            for line in part.splitlines():
                if line.startswith("// MAGIC "):
                    md.append(line[len("// MAGIC ") :])
                elif line.startswith("// MAGIC"):
                    md.append(line[len("// MAGIC") :])
            cells.append({"cell_type": "markdown", "metadata": {}, "source": "\n".join(md)})
        elif part.lstrip().startswith("// MAGIC %run"):
            # Keep as Scala/python magic cell content for Databricks
            src_lines = []
            for line in part.splitlines():
                if line.startswith("// MAGIC "):
                    src_lines.append(line[len("// MAGIC ") :])
                elif line.startswith("// MAGIC"):
                    src_lines.append(line[len("// MAGIC") :])
                else:
                    src_lines.append(line)
            cells.append(
                {
                    "cell_type": "code",
                    "metadata": {},
                    "outputs": [],
                    "execution_count": None,
                    "source": "\n".join(src_lines),
                }
            )
        else:
            cells.append(
                {
                    "cell_type": "code",
                    "metadata": {},
                    "outputs": [],
                    "execution_count": None,
                    "source": part,
                }
            )
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "language_info": {"name": "scala"},
            "kernelspec": {"display_name": "Scala", "language": "scala", "name": "scala"},
        },
        "cells": cells,
    }


def main() -> int:
    out_dir = NB_DIR / "_ipynb"
    out_dir.mkdir(exist_ok=True)
    files = sorted(NB_DIR.glob("*.scala"))
    if not files:
        print("No .scala notebooks found", file=sys.stderr)
        return 1

    for scala in files:
        ipynb = out_dir / f"{scala.stem}.ipynb"
        ipynb.write_text(json.dumps(scala_source_to_ipynb(scala), indent=2), encoding="utf-8")
        remote = f"{WORKSPACE_DIR}/{scala.stem}"
        cmd = [
            "databricks",
            "workspace",
            "import",
            str(ipynb),
            remote,
            "--language",
            "SCALA",
            "--format",
            "JUPYTER",
            "--overwrite",
        ]
        print("Running:", " ".join(cmd))
        subprocess.check_call(cmd)
        print(f"Imported {scala.name} -> {remote}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
