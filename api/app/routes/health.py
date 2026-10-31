"""GET /health: always 200 {"ok": true}, even when the licence has expired.

Owner: B. Filled in by: B0.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
