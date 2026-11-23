.PHONY: install test lint format typecheck run clean build docker docs

PYTHON ?= python
export PYTHONPATH := src

install:
	$(PYTHON) -m pip install -r requirements-dev.txt

test:
	DATABASE_URL=sqlite:///:memory: SEED_ON_START=0 $(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

typecheck:
	$(PYTHON) -m mypy src/finpulse_ai

check: lint typecheck test

run:
	$(PYTHON) -m uvicorn finpulse_ai.main:app --reload --port 8000

build:
	$(PYTHON) -m build

docs:
	$(PYTHON) -m mkdocs serve

docker:
	docker compose up -d --build

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build site *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
