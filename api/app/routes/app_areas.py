"""GET /app/areas: area list for the web app's area picker. UI helper, not judged.

Owner: B. Filled in by: B1.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.shared_data import data_items

router = APIRouter()


@router.get("/app/areas")
def areas() -> dict[str, list[dict[str, Any]]]:
    return {"areas": list(data_items("areas"))}
