"""Loads shared/data/areas.json; pincode lookup and great-circle distance between area points.

Owner: B. Filled in by: B2, B6 (distance).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cache

from app.shared_data import data_items


@dataclass(frozen=True)
class Area:
    pincode: str
    locality: str
    city: str
    lat: float
    lng: float


@cache
def areas() -> dict[str, Area]:
    return {
        str(item["pincode"]): Area(
            pincode=str(item["pincode"]),
            locality=str(item["locality"]),
            city=str(item["city"]),
            lat=float(item["lat"]),
            lng=float(item["lng"]),
        )
        for item in data_items("areas")
    }


def is_known(pincode: str) -> bool:
    return pincode in areas()


EARTH_RADIUS_KM = 6371.0


def distance_km(a: str, b: str) -> float:
    """Great-circle distance between two areas' points."""
    pa, pb = areas()[a], areas()[b]
    lat1, lng1, lat2, lng2 = map(math.radians, (pa.lat, pa.lng, pb.lat, pb.lng))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(h, 1.0)))
