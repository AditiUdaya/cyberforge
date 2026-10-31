"""GET /: a short description of the API, so opening the bare address is not an error page.

Not a PRD route, so like every other one it is behind the licence gate.

Owner: B. Filled in by: B9.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()

ROUTES = [
    "GET /health",
    "POST /reports",
    "GET /lookup?type=&value=",
    "GET /map?pincode=&days=7&radius_km=2",
    "GET /alerts?pincode=",
    "POST /admin/reset",
    "POST /challenges",
    "GET /license",
    "POST /license",
]


@router.get("/")
def root() -> dict[str, object]:
    return {
        "name": "Community Scam Map API",
        "ok": True,
        "routes": ROUTES,
    }
