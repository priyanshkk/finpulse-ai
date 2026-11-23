# Contributing to FinPulse AI

This guide gets you from clone to pull request in a few minutes.

## Local setup

Python 3.11+ is required. Use a virtual environment:

```bash
git clone https://github.com/priyanshkk/finpulse-ai.git
cd finpulse-ai
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
cp .env.example .env             # Windows: copy .env.example .env
python -m uvicorn finpulse_ai.main:app --reload --port 8000
```

Set `PYTHONPATH=src` on Windows if the package is not installed. For tests, use an in-memory database and disable seeding: `DATABASE_URL=sqlite:///:memory: SEED_ON_START=0 python -m pytest`.

## Before you open a PR

Run the same checks CI runs:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src/finpulse_ai
```

Add a test for every change. Keep functions typed, never commit `.env` or API keys.

## Branches and commits

Create a branch from `main` with a conventional prefix: `feat/login`, `fix/currency-rounding`, `docs/docker-guide`, `test/ocr-fallback`. Write commit messages in Conventional Commits form: `feat: add PDF export for monthly invoices`, `fix: resolve currency rounding issue in dashboard`, `docs: add docker setup instructions`.

## Pull request steps

1. Rebase on the latest `main` and confirm the four checks above pass.
2. Describe what changed and how you verified it; attach a screenshot for UI work.
3. Link the related issue and request one reviewer. Keep PRs focused — one idea per PR.

By contributing you agree that your work is licensed under MIT.
