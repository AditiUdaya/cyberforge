"""Licence suite: valid, tampered, wrong key, expiry mid-run, hot swap,
restart, clock rollback, reset.

Owner: B. Filled in by: B3.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.clock import FixedClock
from tests.conftest import LicenceMaker, sign_licence

EXPIRED = {"error": "LICENSE_EXPIRED"}
REPORT: dict[str, Any] = {
    "report_id": "rep_1",
    "occurred_at": "2026-10-27T18:21:04+05:30",
    "reporter_id": "r_1",
    "ip_prefix": "103.21.58",
    "channel": "Phone call",
    "scam_type": "digital-arrest",
    "identifier_type": "phone",
    "identifier_value": "+91 98765 43210",
    "pincode": "560102",
}
CHALLENGE = {
    "identifier_type": "phone",
    "identifier_value": "+91 80 4100 2233",
    "claimant_name": "Fresh Bakes",
    "contact_email": "owner@example.com",
    "proof_note": "GST certificate",
}

LOCKED_CALLS: list[tuple[str, str, dict[str, Any]]] = [
    ("GET", "/lookup", {"params": {"type": "phone", "value": "+919876543210"}}),
    ("POST", "/reports", {"json": REPORT}),
    ("GET", "/map", {"params": {"pincode": "560102"}}),
    ("GET", "/alerts", {"params": {"pincode": "560102"}}),
    ("POST", "/admin/reset", {}),
    ("POST", "/challenges", {"json": CHALLENGE}),
    ("GET", "/app/areas", {}),
    ("GET", "/no-such-route", {}),
]


def lookup(c: TestClient) -> Any:
    return c.get("/lookup", params={"type": "phone", "value": "+919876543210"})


def assert_locked(c: TestClient) -> None:
    for method, path, kwargs in LOCKED_CALLS:
        response = c.request(method, path, **kwargs)
        assert (response.status_code, response.json()) == (403, EXPIRED), f"{method} {path}"
    assert c.get("/health").status_code == 200
    assert c.get("/license").status_code == 200


def test_no_licence_locks_everything_but_health_and_license(bare_client: TestClient) -> None:
    assert_locked(bare_client)
    assert bare_client.get("/license").json() == {
        "licensee": None,
        "expires_at": None,
        "valid": False,
    }


def test_valid_licence_unlocks_and_is_shown(bare_client: TestClient, licence: LicenceMaker) -> None:
    sent = licence("Demo Bank", days=30)
    response = bare_client.post("/license", json=sent)
    assert response.status_code == 200
    shown = {"licensee": "Demo Bank", "expires_at": sent["expires_at"], "valid": True}
    assert response.json() == shown
    assert bare_client.get("/license").json() == shown
    assert lookup(bare_client).status_code == 200


def test_tampered_expiry_is_rejected(bare_client: TestClient, licence: LicenceMaker) -> None:
    sent = licence(minutes=5)
    sent["expires_at"] = "2099-01-01T00:00:00+05:30"
    response = bare_client.post("/license", json=sent)
    assert response.status_code == 400
    assert "error" in response.json()
    assert lookup(bare_client).status_code == 403


def test_tampered_licensee_is_rejected(bare_client: TestClient, licence: LicenceMaker) -> None:
    sent = licence("Demo Bank", days=30) | {"licensee": "Other Bank"}
    assert bare_client.post("/license", json=sent).status_code == 400


def test_wrong_key_is_rejected(bare_client: TestClient, clock: FixedClock) -> None:
    expires = (clock.now() + timedelta(days=30)).isoformat()
    sent = sign_licence("Demo Bank", expires, key=Ed25519PrivateKey.generate())
    assert bare_client.post("/license", json=sent).status_code == 400
    assert lookup(bare_client).status_code == 403


@pytest.mark.parametrize("signature", ["not base64 !!", "", "AAAA"])
def test_garbage_signature_is_rejected(
    bare_client: TestClient, licence: LicenceMaker, signature: str
) -> None:
    sent = licence(days=30) | {"signature": signature}
    assert bare_client.post("/license", json=sent).status_code == 400


@pytest.mark.parametrize("expires_at", ["2026-12-01T00:00:00", "next year", ""])
def test_bad_expiry_text_is_rejected(bare_client: TestClient, expires_at: str) -> None:
    sent = sign_licence("Demo Bank", expires_at)
    assert bare_client.post("/license", json=sent).status_code == 400


def test_already_expired_licence_is_rejected(
    bare_client: TestClient, licence: LicenceMaker
) -> None:
    assert bare_client.post("/license", json=licence(minutes=-1)).status_code == 400


def test_bad_upload_keeps_the_licence_in_force(client: TestClient, licence: LicenceMaker) -> None:
    before = client.get("/license").json()
    bad = licence(days=30) | {"signature": "AAAA"}
    assert client.post("/license", json=bad).status_code == 400
    assert client.get("/license").json() == before
    assert lookup(client).status_code == 200


def test_prd_four_step_demo_without_restart(
    bare_client: TestClient, licence: LicenceMaker, clock: FixedClock
) -> None:
    c = bare_client
    # 1. Working, with GET /license showing who and until when.
    assert c.post("/license", json=licence("Demo Bank", days=1)).status_code == 200
    assert c.post("/reports", json=REPORT).status_code == 201
    assert c.get("/license").json()["valid"] is True
    # 2. Upload a licence that expires in 5 minutes.
    assert c.post("/license", json=licence("Demo Bank", minutes=5)).status_code == 200
    assert lookup(c).status_code == 200
    # 3. After 5 minutes, everything but /health and /license is locked.
    clock.advance(timedelta(minutes=5))
    assert_locked(c)
    assert c.get("/license").json()["valid"] is False
    # 4. A new licence works at once, with the old data still there.
    assert c.post("/license", json=licence("Demo Bank", days=365)).status_code == 200
    body = lookup(c).json()
    assert body["report_count"] == 1


def test_expiry_is_exclusive(client: TestClient, licence: LicenceMaker, clock: FixedClock) -> None:
    client.post("/license", json=licence(minutes=5))
    clock.advance(timedelta(minutes=5) - timedelta(seconds=1))
    assert lookup(client).status_code == 200
    clock.advance(timedelta(seconds=1))
    assert lookup(client).status_code == 403


def test_licence_survives_restart(make_app: Callable[[], FastAPI], licence: LicenceMaker) -> None:
    with TestClient(make_app()) as first:
        first.post("/license", json=licence("Demo Bank", days=30))
    with TestClient(make_app()) as second:
        assert lookup(second).status_code == 200
        assert second.get("/license").json()["licensee"] == "Demo Bank"


def test_clock_set_back_is_refused(client: TestClient, clock: FixedClock) -> None:
    now = clock.now()
    clock.set(now - timedelta(days=365))
    assert lookup(client).status_code == 403
    clock.set(now)
    assert lookup(client).status_code == 200


def test_small_clock_wobble_is_tolerated(client: TestClient, clock: FixedClock) -> None:
    clock.advance(timedelta(minutes=10))
    assert lookup(client).status_code == 200
    clock.advance(timedelta(seconds=-30))
    assert lookup(client).status_code == 200


def test_clock_set_back_cannot_revive_an_expired_licence(
    client: TestClient, licence: LicenceMaker, clock: FixedClock
) -> None:
    client.post("/license", json=licence(minutes=5))
    clock.advance(timedelta(minutes=10))
    assert lookup(client).status_code == 403
    clock.advance(timedelta(minutes=-8))
    assert lookup(client).status_code == 403


def test_high_water_mark_survives_restart(
    make_app: Callable[[], FastAPI], licence: LicenceMaker, clock: FixedClock
) -> None:
    with TestClient(make_app()) as first:
        first.post("/license", json=licence(days=30))
        clock.advance(timedelta(days=2))
        assert lookup(first).status_code == 200
    clock.advance(timedelta(days=-2))
    with TestClient(make_app()) as second:
        assert lookup(second).status_code == 403


def test_reset_keeps_the_licence(client: TestClient) -> None:
    before = client.get("/license").json()
    assert client.post("/admin/reset").status_code == 200
    assert client.get("/license").json() == before
    assert lookup(client).status_code == 200


def test_expiry_never_deletes_data(
    client: TestClient, licence: LicenceMaker, clock: FixedClock
) -> None:
    client.post("/reports", json=REPORT)
    client.post("/license", json=licence(minutes=1))
    clock.advance(timedelta(hours=1))
    assert client.post("/admin/reset").status_code == 403
    client.post("/license", json=licence(days=1))
    assert lookup(client).json()["report_count"] == 1


def test_missing_fields_are_400(bare_client: TestClient) -> None:
    sent = {"licensee": "Demo Bank", "expires_at": "2026-11-15T10:05:00+05:30"}
    response = bare_client.post("/license", json=sent)
    assert response.status_code == 400
    assert "error" in response.json()
