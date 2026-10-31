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
from app.core.identity import Keyring
from app.db import Database, connect, db_path_from_env
from app.license import gate
from app.license.state import LicenceState
from app.license.verify import load_public_key
from app.migrate import apply_migrations
from app.routes import admin, alerts, app_areas, challenges, health, license, lookup, reports
from app.routes import map as map_route


def create_app(
    db_path: Path | None = None,
    clock: Clock | None = None,
    hmac_key: str | None = None,
    public_key_pem: bytes | None = None,
) -> FastAPI:
    """Settings left as None come from the environment when the app starts."""
    path = db_path if db_path is not None else db_path_from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.keyring = Keyring(hmac_key) if hmac_key is not None else Keyring.from_env()
        conn = connect(path)
        apply_migrations(conn)
        app.state.db = Database(conn)
        app.state.licence = LicenceState(app.state.db, load_public_key(public_key_pem))
        try:
            yield
        finally:
            app.state.db.close()

    app = FastAPI(
        title="Community Scam Map API",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.clock = clock if clock is not None else SystemClock()
    errors.install(app)
    gate.install(app)
    routes = (health, reports, lookup, map_route, alerts, admin, challenges, license, app_areas)
    for route in routes:
        app.include_router(route.router)
    return app


app = create_app()
