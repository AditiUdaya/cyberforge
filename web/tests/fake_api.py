"""A stand-in for the API, so screens can be tested without a server.

Owner: A. Filled in by: A5.
"""

from __future__ import annotations

from typing import Any

from scam_web.api_client import ApiError, LicenceExpired

AREAS = [
    {
        "pincode": "560102",
        "locality": "HSR Layout",
        "city": "Bengaluru",
        "lat": 12.9116,
        "lng": 77.6473,
        "source": "prd",
    },
    {
        "pincode": "560034",
        "locality": "Koramangala",
        "city": "Bengaluru",
        "lat": 12.9352,
        "lng": 77.6245,
        "source": "prd",
    },
]

KNOWN = {
    "verdict": "KNOWN_SCAM",
    "report_count": 9,
    "distinct_reporters": 7,
    "first_seen": "2026-10-14T09:12:00+05:30",
    "last_seen": "2026-10-27T18:21:04+05:30",
    "scam_type": "digital-arrest",
    "display_value": "+919876543210",
    "evidence": [
        {
            "occurred_at": "2026-10-27T18:21:04+05:30",
            "channel": "Phone call",
            "scam_type": "digital-arrest",
            "pincode": "560102",
        },
    ],
    "challenged": False,
}
UNREPORTED = {
    "verdict": "NO_REPORTS",
    "report_count": 0,
    "distinct_reporters": 0,
    "first_seen": None,
    "last_seen": None,
    "scam_type": None,
    "display_value": "sbi***.in/...",
    "evidence": [],
    "challenged": False,
}


class FakeApi:
    def __init__(self, *, expired: bool = False, report_status: int = 201) -> None:
        self.expired = expired
        self.report_status = report_status
        self.reports: list[dict[str, Any]] = []
        self.challenges: list[dict[str, Any]] = []
        self.uploaded: list[dict[str, Any]] = []
        self.clusters: list[dict[str, Any]] = []
        self.found_alerts: list[dict[str, Any]] = []
        self.licence_body: dict[str, Any] = {
            "licensee": "Demo Bank",
            "expires_at": "2027-10-31T19:54:26+05:30",
            "valid": True,
        }

    def _gate(self) -> None:
        if self.expired:
            raise LicenceExpired

    def lookup(self, kind: str, value: str) -> dict[str, Any]:
        self._gate()
        return dict(KNOWN) if kind == "phone" else dict(UNREPORTED)

    def report(self, body: dict[str, Any]) -> dict[str, Any]:
        self._gate()
        if self.report_status != 201:
            raise ApiError(self.report_status, "refused")
        self.reports.append(body)
        return {"report_id": body["report_id"], "case_id": "case_1", "merged": False}

    def area_map(self, pincode: str, days: float, radius_km: float) -> list[dict[str, Any]]:
        self._gate()
        return self.clusters

    def alerts(self, pincode: str) -> list[dict[str, Any]]:
        self._gate()
        return self.found_alerts

    def challenge(self, body: dict[str, Any]) -> dict[str, Any]:
        self._gate()
        self.challenges.append(body)
        return {"challenge_id": "chl_1", "status": "under_review"}

    def licence(self) -> dict[str, Any]:
        return self.licence_body

    def upload_licence(self, doc: dict[str, Any]) -> dict[str, Any]:
        self.uploaded.append(doc)
        return self.licence_body

    def areas(self) -> list[dict[str, Any]]:
        self._gate()
        return AREAS
