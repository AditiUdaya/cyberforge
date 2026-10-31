"""Middleware run on every request: expired means 403 LICENSE_EXPIRED except /health and /license.

Owner: B. Filled in by: B3.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.clock import Clock
from app.errors import LICENSE_EXPIRED, error_response
from app.license.state import LicenceState

OPEN_PATHS = frozenset({"/health", "/license"})


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def licence_gate(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path in OPEN_PATHS:
            return await call_next(request)
        state: LicenceState = request.app.state.licence
        clock: Clock = request.app.state.clock
        if not state.is_valid(clock.now()):
            return error_response(403, LICENSE_EXPIRED)
        return await call_next(request)
