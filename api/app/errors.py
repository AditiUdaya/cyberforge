"""Error replies shaped {"error": "..."}, including exactly 403 {"error": "LICENSE_EXPIRED"}.
No identifiers, notes or query strings in any message.

Owner: B. Filled in by: B1.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

LICENSE_EXPIRED = "LICENSE_EXPIRED"

_HTTP_MESSAGES = {
    404: "not found",
    405: "method not allowed",
}


def error_response(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})


def _describe(exc: RequestValidationError) -> str:
    """Name the offending fields only; never echo the values that were sent."""
    problems: list[str] = []
    for err in exc.errors():
        loc = [str(part) for part in err.get("loc", ()) if part not in ("body", "query")]
        field = ".".join(loc) or "body"
        kind = str(err.get("type", "invalid"))
        if kind == "missing":
            problems.append(f"missing {field}")
        elif kind == "json_invalid":
            problems.append("body is not valid JSON")
        else:
            problems.append(f"invalid {field}")
    return "; ".join(dict.fromkeys(problems)) or "invalid request"


async def _validation(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return error_response(400, "invalid request")
    return error_response(400, _describe(exc))


async def _http(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, HTTPException):
        return error_response(500, "internal error")
    message = _HTTP_MESSAGES.get(exc.status_code, str(exc.detail))
    return JSONResponse(
        status_code=exc.status_code, content={"error": message}, headers=exc.headers
    )


async def _unhandled(_: Request, __: Exception) -> JSONResponse:
    return error_response(500, "internal error")


def install(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation)
    app.add_exception_handler(HTTPException, _http)
    app.add_exception_handler(Exception, _unhandled)
