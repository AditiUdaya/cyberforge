"""Loads shared/data/areas.json; pincode lookup and great-circle distance between area points.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

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
