"""FastAPI app factory: mounts the licence gate, the PRD routes and /app/* helpers.

The web app is a separate Streamlit service (DECISIONS D55), so nothing static is served here.

Owner: B. Filled in by: B0.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app import errors
from app.clock import Clock, SystemClock
from app.db import connect, db_path_from_env
from app.migrate import apply_migrations
from app.routes import admin, alerts, app_areas, challenges, health, license, lookup, reports
from app.routes import map as map_route


def create_app(db_path: Path | None = None, clock: Clock | None = None) -> FastAPI:
    path = db_path if db_path is not None else db_path_from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        conn = connect(path)
        apply_migrations(conn)
        app.state.db = conn
        try:
            yield
        finally:
            conn.close()

    app = FastAPI(
        title="Community Scam Map API",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.clock = clock if clock is not None else SystemClock()
    errors.install(app)
    routes = (health, reports, lookup, map_route, alerts, admin, challenges, license, app_areas)
    for route in routes:
        app.include_router(route.router)
    return app


app = create_app()
