"""GET /map?pincode&days=7&radius_km=2: one cluster per area in radius and window.
Area points from shared/data/areas.json only; counted reports only.

Owner: B. Filled in by: B6.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import store
from app.clock import Clock
from app.core import mapview
from app.core.areas import is_known
from app.core.validate import to_utc_text
from app.db import Database
from app.deps import get_clock, get_db
from app.errors import error_response

router = APIRouter()

PINCODE = r"^[0-9]{6}$"


class Cluster(BaseModel):
    pincode: str
    locality: str
    city: str
    count: int
    top_scam_type: str
    severity: Literal["CRIT", "HIGH", "MED"]
    lat: float
    lng: float


class MapOut(BaseModel):
    clusters: list[Cluster]


@router.get("/map", response_model=MapOut)
def area_map(
    pincode: Annotated[str, Query(pattern=PINCODE)],
    db: Annotated[Database, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
    days: Annotated[float, Query(gt=0, le=3650)] = 7,
    radius_km: Annotated[float, Query(ge=0, le=5000)] = 2,
) -> MapOut | JSONResponse:
    if not is_known(pincode):
        return error_response(400, "invalid pincode: not a known area")
    now = clock.now()
    nearby = mapview.areas_within(pincode, radius_km)
    with db.read() as conn:
        counts = store.area_counts(
            conn, nearby, to_utc_text(now - timedelta(days=days)), to_utc_text(now)
        )
    found = mapview.clusters({p: mapview.AreaCount(n, top) for p, (n, top) in counts.items()})
    return MapOut(
        clusters=[
            Cluster(
                pincode=c.area.pincode,
                locality=c.area.locality,
                city=c.area.city,
                count=c.count,
                top_scam_type=c.top_scam_type,
                severity=c.severity,
                lat=c.area.lat,
                lng=c.area.lng,
            )
            for c in found
        ]
    )
