"""POST /admin/reset: deletes reports, cases, counts, counters and challenges.
Keeps areas, verified values and the licence. No login (PRD Appendix A rule 5).

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app import store
from app.db import Database
from app.deps import get_db

router = APIRouter()


@router.post("/admin/reset")
def reset(db: Annotated[Database, Depends(get_db)]) -> dict[str, bool]:
    with db.write() as conn:
        store.reset(conn)
    return {"ok": True}
