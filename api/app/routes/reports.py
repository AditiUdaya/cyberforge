"""POST /reports: validate, normalise, HMAC reporter fields, rate limit (429), store.
Replies 201 {report_id, case_id, merged}, 400, or 429 for a reporter over the hourly limit.

Owner: B. Filled in by: B2, B5 (429 and note fingerprints).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app import activity, store
from app.clock import Clock
from app.core import validate
from app.core.areas import is_known
from app.core.identity import Keyring, connection_prefix
from app.core.normalise import IdentifierType, InvalidIdentifier, normalise
from app.core.notes import sketch
from app.core.trust_config import RATE_LIMIT_PER_HOUR
from app.core.verified import is_verified
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
        _rejected(db, now, body, f"invalid {body.identifier_type}")
        return error_response(400, f"invalid identifier_value for type {body.identifier_type}")
    except validate.InvalidReport as e:
        _rejected(db, now, body, _reason(str(e)))
        return error_response(400, str(e))

    reported = validate.reported_at(body.reported_at, occurred, now)
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
        reported_at=validate.to_utc_text(reported),
        note_length=len(body.note.strip()),
        note_sketch=sketch(body.note, keys.note_key()),
        has_screenshot=body.has_screenshot,
        amount_lost_inr=body.amount_lost_inr,
        origin="api" if body.ip_prefix else "web",
    )
    fresh = not activity.too_old(occurred, now)  # incidents 30+ days old never show as activity
    ctx = activity.Context(
        at=now,
        occurred=occurred,
        pincode=pincode,
        scam_type=new.scam_type,
        channel=new.channel,
        identifier_type=body.identifier_type,
        display=activity.masked(body.identifier_type, normalised),
    )
    with db.write() as conn:
        if store.recent_reports(conn, new.reporter_hmac, reported) >= RATE_LIMIT_PER_HOUR:
            if fresh:
                activity.record(conn, "rate_limited", ctx, group=True)
            return error_response(429, "too many reports from this reporter; try again later")
        before = store.find_case(conn, new.identifier_type, new.identifier_hmac)
        case_id, merged, status = store.add_report(conn, new)
        after = store.find_case(conn, new.identifier_type, new.identifier_hmac)
        if after is not None and fresh:
            activity.report_events(
                conn,
                replace(ctx, case_id=case_id),
                status=status,
                before=before,
                after=after,
                verified=is_verified(body.identifier_type, normalised),
            )
    return ReportOut(report_id=body.report_id, case_id=case_id, merged=merged)


def _reason(message: str) -> str:
    """A short reason for the activity feed, from a rejection message that holds no input."""
    if message.startswith("invalid pincode"):
        return "unknown area"
    if "future" in message:
        return "time in the future"
    return "invalid time"


def _rejected(db: Database, now: datetime, body: ReportIn, reason: str) -> None:
    """Show a rejection in the feed: the reason and, for a real area, where. Never the value."""
    try:
        if activity.too_old(validate.parse_time(body.occurred_at, field="occurred_at"), now):
            return  # a rejected report about an old incident is not shown either
    except validate.InvalidReport:
        pass
    pincode = body.pincode.strip() if is_known(body.pincode.strip()) else None
    with db.write() as conn:
        where = activity.Context(at=now, pincode=pincode)
        activity.record(conn, "rejected", where, detail=reason, group=True)
