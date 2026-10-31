"""GET /lookup?type&value: verdict, counts, masked display_value, evidence, challenged.
Unreported is 200 NO_REPORTS; invalid is 400.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import store
from app.core.identity import Keyring
from app.core.mask import display_value
from app.core.normalise import IdentifierType, InvalidIdentifier, normalise
from app.core.trust_config import EVIDENCE_LIMIT
from app.core.validate import to_display
from app.core.verdict import CaseFacts, Verdict, verdict
from app.core.verified import is_verified
from app.db import Database
from app.deps import get_db, get_keyring
from app.errors import error_response

router = APIRouter()


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


@router.get("/lookup", response_model=LookupOut)
def lookup(
    type: Annotated[IdentifierType, Query()],
    value: Annotated[str, Query(min_length=1)],
    db: Annotated[Database, Depends(get_db)],
    keys: Annotated[Keyring, Depends(get_keyring)],
) -> LookupOut | JSONResponse:
    try:
        normalised = normalise(type, value)
    except InvalidIdentifier:
        return error_response(400, f"invalid value for type {type}")

    verified = is_verified(type, normalised)
    with db.read() as conn:
        case = store.find_case(conn, type, keys.identifier(type, normalised))
        rows = store.evidence(conn, case.case_id, EVIDENCE_LIMIT) if case else []

    if case is None:
        facts = CaseFacts(report_count=0, clusters=0, weighted_score=0.0, challenged=False)
    else:
        facts = CaseFacts(
            report_count=case.report_count,
            clusters=case.distinct_reporters,
            weighted_score=case.weighted_score,
            challenged=case.challenged,
        )
    result = verdict(facts, verified=verified)
    reporters = case.distinct_reporters if case else 0
    return LookupOut(
        verdict=result,
        report_count=facts.report_count,
        distinct_reporters=reporters,
        first_seen=to_display(case.first_seen) if case and case.first_seen else None,
        last_seen=to_display(case.last_seen) if case and case.last_seen else None,
        scam_type=case.top_scam_type if case else None,
        # Verified values are public numbers; everything else stays masked below 3 people.
        display_value=normalised if verified else display_value(type, normalised, reporters),
        # Evidence on a verified value would only help an attacker tune a campaign.
        evidence=[]
        if verified
        else [
            Evidence(
                occurred_at=to_display(r.occurred_at),
                channel=r.channel,
                scam_type=r.scam_type,
                pincode=r.pincode,
            )
            for r in rows
        ],
        challenged=facts.challenged,
    )
