"""GET /map?pincode&days=7&radius_km=2: one cluster per area in radius and window.
Area points from shared/data/areas.json only. Stub in B1.

B1 stub: validates the query and returns no clusters.

Owner: B. Filled in by: B6.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

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


@router.get("/map")
def area_map(
    pincode: Annotated[str, Query(pattern=PINCODE)],
    days: Annotated[float, Query(gt=0)] = 7,
    radius_km: Annotated[float, Query(ge=0)] = 2,
) -> MapOut:
    return MapOut(clusters=[])
