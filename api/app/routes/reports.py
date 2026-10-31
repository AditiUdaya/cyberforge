"""POST /reports: validate, normalise, HMAC reporter fields, rate limit (429), store.
Replies 201 {report_id, case_id, merged} or 400. Stub in B1; trust rules in B5.

B1 stub: checks the body shape only and stores nothing.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter()

IdentifierType = Literal["phone", "upi", "url", "sender_id"]


class ReportIn(BaseModel):
    """PRD Appendix A section 2. Unknown extra fields are ignored, never stored."""

    model_config = ConfigDict(extra="ignore")

    report_id: str = Field(min_length=1)
    occurred_at: str = Field(min_length=1)
    reported_at: str | None = None
    reporter_id: str = Field(min_length=1)
    ip_prefix: str | None = None
    channel: str
    scam_type: str
    identifier_type: IdentifierType
    identifier_value: str
    pincode: str
    locality: str | None = None
    city: str | None = None
    note: str = ""
    has_screenshot: bool = False
    amount_lost_inr: float = Field(default=0, ge=0)


class ReportOut(BaseModel):
    report_id: str
    case_id: str
    merged: bool


@router.post("/reports", status_code=201)
def create_report(report: ReportIn) -> ReportOut:
    return ReportOut(report_id=report.report_id, case_id="case_pending", merged=False)
