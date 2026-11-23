"""FinPulse AI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import get_settings
from .db import SessionLocal, init_db
from .routers import api, web
from .services import seed


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialise the schema and seed demo data on first boot."""
    init_db()
    settings = get_settings()
    if settings.seed_on_start:
        with SessionLocal() as session:
            seed.seed_database(session)
    yield


def create_app() -> FastAPI:
    """Build the FastAPI application with API, web pages and static assets."""
    app = FastAPI(
        title="FinPulse AI",
        description="Self-hosted invoice and expense tracker with AI receipt scanning.",
        version=__version__,
        lifespan=lifespan,
    )
    settings = get_settings()
    app.mount("/static", StaticFiles(directory=str(settings.app_dir / "static")), name="static")
    app.include_router(web.router)
    app.include_router(api.router)
    return app


app = create_app()
