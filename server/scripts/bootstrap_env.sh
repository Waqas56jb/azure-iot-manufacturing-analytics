#!/usr/bin/env bash
# Bootstrap local Python env for server MLOps backend
set -euo pipefail
cd "$(dirname "$0")/.."
python -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
pip install -U pip
pip install -r requirements.txt
cp -n .env.example .env || true
echo "Server env ready. Fill .env with Azure values."
