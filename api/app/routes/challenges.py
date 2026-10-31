"""POST /challenges: a business disputes an identifier; 201 {challenge_id, status: under_review}.
Claimant contact is never returned or logged. Stub in B1.

B1 stub: checks the body shape, issues an id and stores nothing.

Owner: B. Filled in by: B6.
"""

from __future__ import annotations

import secrets
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.routes.reports import IdentifierType

router = APIRouter()


class ChallengeIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    identifier_type: IdentifierType
    identifier_value: str
    claimant_name: str = Field(min_length=1)
    contact_email: str = Field(min_length=3)
    proof_note: str


class ChallengeOut(BaseModel):
    challenge_id: str
    status: Literal["under_review"]


@router.post("/challenges", status_code=201)
def create_challenge(challenge: ChallengeIn) -> ChallengeOut:
    return ChallengeOut(challenge_id=f"chl_{secrets.token_hex(6)}", status="under_review")
