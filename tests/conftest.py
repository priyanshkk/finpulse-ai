"""Shared fixtures. Environment is set before importing the application."""

from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"  # noqa: E402
os.environ["SEED_ON_START"] = "0"  # noqa: E402
os.environ["GEMINI_API_KEY"] = ""  # noqa: E402

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from finpulse_ai.db import Base, SessionLocal, engine  # noqa: E402
from finpulse_ai.main import create_app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database() -> Iterator[None]:
    """Give every test a fresh in-memory schema."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def session() -> Iterator[Session]:
    """Yield a database session that is always closed."""
    with SessionLocal() as value:
        yield value


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Yield a test client with lifespan events enabled."""
    with TestClient(create_app()) as value:
        yield value
