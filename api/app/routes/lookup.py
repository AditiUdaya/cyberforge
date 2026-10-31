"""GET /lookup?type&value: verdict, counts, masked display_value, evidence, challenged.
Unreported is 200 NO_REPORTS; invalid is 400. Stub in B1.

B1 stub: every value is NO_REPORTS with a fully masked display_value.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.routes.reports import IdentifierType

router = APIRouter()

Verdict = Literal["KNOWN_SCAM", "SUSPICIOUS", "NO_REPORTS", "VERIFIED_BUSINESS"]


class Evidence(BaseModel):
    occurred_at: str
    channel: str
    scam_type: str
    pincode: str


class LookupOut(BaseModel):
    verdict: Verdict
    report_count: int
    distinct_reporters: int
    first_seen: str | None
    last_seen: str | None
    scam_type: str | None
    display_value: str
    evidence: list[Evidence]
    challenged: bool


@router.get("/lookup")
def lookup(
    type: Annotated[IdentifierType, Query()],
    value: Annotated[str, Query(min_length=1)],
) -> LookupOut:
    return LookupOut(
        verdict="NO_REPORTS",
        report_count=0,
        distinct_reporters=0,
        first_seen=None,
        last_seen=None,
        scam_type=None,
        display_value="***",
        evidence=[],
        challenged=False,
    )
