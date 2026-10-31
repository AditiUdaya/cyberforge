"""GET /alerts?pincode: SPIKE and NEW_TYPE on counted reports only.
No alerts is {"alerts": []}.

Owner: B. Filled in by: B6.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app import store
from app.clock import Clock
from app.core import alerts as alert_rules
from app.core.areas import is_known
from app.core.validate import to_utc_text
from app.db import Database
from app.deps import get_clock, get_db
from app.errors import error_response
from app.routes.map import PINCODE

router = APIRouter()


@router.get("/alerts", response_model=None)
def alerts(
    pincode: Annotated[str, Query(pattern=PINCODE)],
    db: Annotated[Database, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> dict[str, list[dict[str, Any]]] | JSONResponse:
    if not is_known(pincode):
        return error_response(400, "invalid pincode: not a known area")
    now = clock.now()
    with db.read() as conn:
        events = store.area_events(conn, pincode, to_utc_text(now - alert_rules.HISTORY))
    return {"alerts": alert_rules.alerts(pincode, events, now)}
