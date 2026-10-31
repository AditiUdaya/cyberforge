"""POST /reports: validate, normalise, HMAC reporter fields, rate limit (429), store.
Replies 201 {report_id, case_id, merged} or 400. Trust rules and 429 arrive in B5.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app import store
from app.clock import Clock
from app.core import validate
from app.core.identity import Keyring, connection_prefix
from app.core.normalise import IdentifierType, InvalidIdentifier, normalise
from app.db import Database
from app.deps import get_clock, get_db, get_keyring
from app.errors import error_response

router = APIRouter()


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


@router.post("/reports", status_code=201, response_model=ReportOut)
def create_report(
    body: ReportIn,
    request: Request,
    db: Annotated[Database, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
    keys: Annotated[Keyring, Depends(get_keyring)],
) -> ReportOut | JSONResponse:
    now = clock.now()
    try:
        normalised = normalise(body.identifier_type, body.identifier_value)
        occurred = validate.occurred_at(body.occurred_at, now)
        pincode = validate.pincode(body.pincode)
    except InvalidIdentifier:
        return error_response(400, f"invalid identifier_value for type {body.identifier_type}")
    except validate.InvalidReport as e:
        return error_response(400, str(e))

    prefix = body.ip_prefix
    if not prefix:
        prefix = connection_prefix(request.client.host if request.client else None)
    new = store.NewReport(
        report_id=body.report_id,
        identifier_type=body.identifier_type,
        identifier_hmac=keys.identifier(body.identifier_type, normalised),
        reporter_hmac=keys.reporter(body.reporter_id),
        ip_prefix_hmac=keys.ip_prefix(prefix),
        channel=validate.channel(body.channel),
        scam_type=validate.scam_type(body.scam_type),
        pincode=pincode,
        occurred_at=validate.to_utc_text(occurred),
        reported_at=validate.to_utc_text(now),
        note_length=len(body.note.strip()),
        has_screenshot=body.has_screenshot,
        amount_lost_inr=body.amount_lost_inr,
        origin="api" if body.ip_prefix else "web",
    )
    with db.write() as conn:
        case_id, merged = store.add_report(conn, new)
    return ReportOut(report_id=body.report_id, case_id=case_id, merged=merged)
