"""GET /alerts?pincode: SPIKE and NEW_TYPE on counted reports only.
No alerts is {"alerts": []}. Stub in B1.

B1 stub: validates the query and returns no alerts.

Owner: B. Filled in by: B6.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.routes.map import PINCODE

router = APIRouter()


@router.get("/alerts")
def alerts(pincode: Annotated[str, Query(pattern=PINCODE)]) -> dict[str, list[dict[str, Any]]]:
    return {"alerts": []}
