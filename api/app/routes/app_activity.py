"""GET /app/activity: the live feed for the website's right-hand panel. UI helper, not judged.

Newest events first (masked, grouped, never a reporter field) and every alert live right now.
Behind the licence like every route except /health and /license.

Owner: B. Filled in by: B9.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app import activity
from app.clock import Clock
from app.db import Database
from app.deps import get_clock, get_db

router = APIRouter()


@router.get("/app/activity")
def app_activity(
    db: Annotated[Database, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict[str, list[dict[str, Any]]]:
    with db.read() as conn:
        return activity.feed(conn, clock.now())
