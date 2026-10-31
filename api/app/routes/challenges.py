"""POST /challenges: a business disputes an identifier; 201 {challenge_id, status: under_review}.
While under review, lookups show challenged: true and are never KNOWN_SCAM.
The claimant's name and email are stored for review only: never returned or logged.

Owner: B. Filled in by: B6.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app import activity, store
from app.clock import Clock
from app.core.identity import Keyring
from app.core.normalise import IdentifierType, InvalidIdentifier, normalise
from app.core.validate import to_utc_text
from app.db import Database
from app.deps import get_clock, get_db, get_keyring
from app.errors import error_response

router = APIRouter()


class ChallengeIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    identifier_type: IdentifierType
    identifier_value: str
    claimant_name: str = Field(min_length=1, max_length=200)
    contact_email: str = Field(min_length=3, max_length=254)
    proof_note: str = Field(max_length=2000)


class ChallengeOut(BaseModel):
    challenge_id: str
    status: Literal["under_review"]


@router.post("/challenges", status_code=201, response_model=ChallengeOut)
def create_challenge(
    body: ChallengeIn,
    db: Annotated[Database, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
    keys: Annotated[Keyring, Depends(get_keyring)],
) -> ChallengeOut | JSONResponse:
    try:
        normalised = normalise(body.identifier_type, body.identifier_value)
    except InvalidIdentifier:
        return error_response(400, f"invalid identifier_value for type {body.identifier_type}")
    identifier_hmac = keys.identifier(body.identifier_type, normalised)
    with db.write() as conn:
        # One dispute per number. The PRD allows 429 for slowing someone down, and the check and
        # the insert share one transaction, so two at once cannot both get through.
        if store.has_challenge(conn, body.identifier_type, identifier_hmac):
            return error_response(
                429, "a dispute is already under review for this number; only one is allowed"
            )
        challenge_id = store.add_challenge(
            conn,
            identifier_type=body.identifier_type,
            identifier_hmac=identifier_hmac,
            claimant_name=body.claimant_name.strip(),
            contact_email=body.contact_email.strip(),
            proof_note=body.proof_note.strip(),
            created=to_utc_text(clock.now()),
        )
        where = activity.Context(
            at=clock.now(),
            identifier_type=body.identifier_type,
            display=activity.masked(body.identifier_type, normalised),
        )
        activity.record(conn, "dispute", where)
    return ChallengeOut(challenge_id=challenge_id, status="under_review")
