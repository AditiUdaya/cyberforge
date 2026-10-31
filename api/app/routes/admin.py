"""POST /admin/reset: deletes reports, cases, counts, counters and challenges.
Keeps areas, verified values and the licence. Stub in B1.

B1 stub: nothing is stored yet, so there is nothing to delete.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.post("/admin/reset")
def reset() -> dict[str, bool]:
    return {"ok": True}
