"""GET /license and POST /license: show the licence;
verify and hot-swap a new one without a restart.
Both work when expired. Stub in B1.

B1 stub: no licence is loaded, and every upload is refused because nothing can verify it yet.

Owner: B. Filled in by: B3.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.errors import error_response

router = APIRouter()


class LicenseIn(BaseModel):
    licensee: str = Field(min_length=1)
    expires_at: str = Field(min_length=1)
    signature: str = Field(min_length=1)


class LicenseOut(BaseModel):
    licensee: str | None
    expires_at: str | None
    valid: bool


@router.get("/license")
def get_license() -> LicenseOut:
    return LicenseOut(licensee=None, expires_at=None, valid=False)


@router.post("/license", response_model=LicenseOut)
def post_license(licence: LicenseIn) -> JSONResponse:
    return error_response(400, "signature could not be verified")
