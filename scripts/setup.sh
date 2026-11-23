#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install --disable-pip-version-check -q -r requirements-dev.txt
[ -f .env ] || cp .env.example .env

export PYTHONPATH=src DATABASE_URL="sqlite:///:memory:" SEED_ON_START=0
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy src/finpulse_ai
echo "Done. Activate with: source .venv/bin/activate"
