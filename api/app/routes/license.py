"""GET /license and POST /license: show the licence;
verify and hot-swap a new one without a restart.
Both work when expired.

Owner: B. Filled in by: B3.
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.clock import Clock
from app.deps import get_clock
from app.errors import error_response
from app.license.state import LicenceState
from app.license.verify import InvalidLicence

router = APIRouter()


class LicenseIn(BaseModel):
    licensee: str = Field(min_length=1)
    expires_at: str = Field(min_length=1)
    signature: str = Field(min_length=1)


class LicenseOut(BaseModel):
    licensee: str | None
    expires_at: str | None
    valid: bool


def get_licence_state(request: Request) -> LicenceState:
    return cast(LicenceState, request.app.state.licence)


@router.get("/license")
def get_license(
    state: Annotated[LicenceState, Depends(get_licence_state)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> LicenseOut:
    valid = state.is_valid(clock.now())
    licence = state.licence
    if licence is None:
        return LicenseOut(licensee=None, expires_at=None, valid=False)
    return LicenseOut(licensee=licence.licensee, expires_at=licence.expires_at_text, valid=valid)


@router.post("/license", response_model=LicenseOut)
def post_license(
    body: LicenseIn,
    state: Annotated[LicenceState, Depends(get_licence_state)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> LicenseOut | JSONResponse:
    try:
        licence = state.install(body.model_dump(), clock.now())
    except InvalidLicence as e:
        return error_response(400, str(e))
    return LicenseOut(
        licensee=licence.licensee,
        expires_at=licence.expires_at_text,
        valid=state.is_valid(clock.now()),
    )
