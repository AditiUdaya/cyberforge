"""Talks to the API over HTTPS. Every expired-licence reply becomes LicenceExpired, so each
screen can show the PRD's expired message the same way.

Owner: A. Filled in by: A1.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from scam_web.settings import api_url

LICENSE_EXPIRED = "LICENSE_EXPIRED"


class LicenceExpired(Exception):
    """The API answered 403 LICENSE_EXPIRED."""


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class Api(Protocol):
    def lookup(self, kind: str, value: str) -> dict[str, Any]: ...
    def report(self, body: dict[str, Any]) -> dict[str, Any]: ...
    def area_map(self, pincode: str, days: float, radius_km: float) -> list[dict[str, Any]]: ...
    def alerts(self, pincode: str) -> list[dict[str, Any]]: ...
    def challenge(self, body: dict[str, Any]) -> dict[str, Any]: ...
    def licence(self) -> dict[str, Any]: ...
    def upload_licence(self, doc: dict[str, Any]) -> dict[str, Any]: ...
    def areas(self) -> list[dict[str, Any]]: ...


class HttpApi:
    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self._client = httpx.Client(base_url=base_url or api_url(), timeout=timeout)

    def _call(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.HTTPError:
            raise ApiError(0, "server unreachable") from None
        try:
            body = response.json()
        except ValueError:
            body = {}
        if response.status_code == 403 and body.get("error") == LICENSE_EXPIRED:
            raise LicenceExpired
        if response.status_code >= 400:
            raise ApiError(response.status_code, str(body.get("error", "request failed")))
        return body

    def lookup(self, kind: str, value: str) -> dict[str, Any]:
        result: dict[str, Any] = self._call("GET", "/lookup", params={"type": kind, "value": value})
        return result

    def report(self, body: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = self._call("POST", "/reports", json=body)
        return result

    def area_map(self, pincode: str, days: float, radius_km: float) -> list[dict[str, Any]]:
        params = {"pincode": pincode, "days": str(days), "radius_km": str(radius_km)}
        clusters: list[dict[str, Any]] = self._call("GET", "/map", params=params)["clusters"]
        return clusters

    def alerts(self, pincode: str) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = self._call("GET", "/alerts", params={"pincode": pincode})[
            "alerts"
        ]
        return found

    def challenge(self, body: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = self._call("POST", "/challenges", json=body)
        return result

    def licence(self) -> dict[str, Any]:
        result: dict[str, Any] = self._call("GET", "/license")
        return result

    def upload_licence(self, doc: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = self._call("POST", "/license", json=doc)
        return result

    def areas(self) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = self._call("GET", "/app/areas")["areas"]
        return found
