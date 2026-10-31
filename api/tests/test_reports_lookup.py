"""POST /reports, GET /lookup and POST /admin/reset behaviour (task B2).

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

REPORT: dict[str, Any] = {
    "report_id": "rep_000123",
    "occurred_at": "2026-10-27T18:21:04+05:30",
    "reported_at": "2026-10-27T18:40:04+05:30",
    "reporter_id": "r_7c2d91aa",
    "ip_prefix": "103.21.58",
    "channel": "Phone call",
    "scam_type": "digital-arrest",
    "identifier_type": "phone",
    "identifier_value": "+91 98765 43210",
    "pincode": "560102",
    "locality": "HSR Layout",
    "city": "Bengaluru",
    "note": "Video call from a man in police uniform asking for money",
    "has_screenshot": False,
    "amount_lost_inr": 0,
}


def report(client: TestClient, **changes: Any) -> Any:
    return client.post("/reports", json=REPORT | changes)


def lookup(client: TestClient, kind: str, value: str) -> Any:
    return client.get("/lookup", params={"type": kind, "value": value})


def by(n: int) -> dict[str, Any]:
    """Fields that make report n come from a different, unrelated person."""
    return {
        "report_id": f"rep_{n}",
        "reporter_id": f"r_person_{n}",
        "ip_prefix": f"10.{n}.7",
        "note": f"Person {n} describes the call in their own words, story number {n * 7919}",
    }


def test_unreported_is_200_no_reports_and_masked(client: TestClient) -> None:
    body = lookup(client, "phone", "+91 91234 56780").json()
    assert body["verdict"] == "NO_REPORTS"
    assert (body["report_count"], body["distinct_reporters"]) == (0, 0)
    assert body["display_value"] == "91XXXXX780"
    assert body["evidence"] == [] and body["challenged"] is False


@pytest.mark.parametrize(
    ("kind", "value"),
    [("phone", "12345"), ("phone", "test"), ("upi", "nope"), ("url", "test"), ("sender_id", "X")],
)
def test_junk_lookup_is_400(client: TestClient, kind: str, value: str) -> None:
    response = lookup(client, kind, value)
    assert response.status_code == 400
    assert value not in response.json()["error"]


def test_report_then_lookup_in_every_prd_format(client: TestClient) -> None:
    first = report(client)
    assert first.status_code == 201
    assert first.json()["merged"] is False
    for value in ["+91 98765 43210", "09876543210", "98765-43210", "919876543210"]:
        body = lookup(client, "phone", value).json()
        assert body["verdict"] == "SUSPICIOUS"
        assert (body["report_count"], body["distinct_reporters"]) == (1, 1)
        assert body["display_value"] == "98XXXXX210"
        assert body["scam_type"] == "digital-arrest"
        assert body["first_seen"] == body["last_seen"] == "2026-10-27T18:21:04+05:30"
        assert body["evidence"] == [
            {
                "occurred_at": "2026-10-27T18:21:04+05:30",
                "channel": "Phone call",
                "scam_type": "digital-arrest",
                "pincode": "560102",
            }
        ]


def test_second_report_merges_into_the_same_case(client: TestClient) -> None:
    a = report(client, **by(1)).json()
    b = report(client, **by(2), identifier_value="09876543210").json()
    assert b["merged"] is True
    assert a["case_id"] == b["case_id"]
    assert b["report_id"] == "rep_2"


def test_three_people_make_known_scam_and_unmask(client: TestClient) -> None:
    for n in (1, 2, 3):
        assert report(client, **by(n)).status_code == 201
    body = lookup(client, "phone", "09876543210").json()
    assert body["verdict"] == "KNOWN_SCAM"
    assert body["distinct_reporters"] == 3
    assert body["display_value"] == "+919876543210"


def test_one_person_many_times_is_one_reporter(client: TestClient) -> None:
    for n in (1, 2, 3):
        report(client, report_id=f"rep_{n}")
    body = lookup(client, "phone", "+919876543210").json()
    assert (body["report_count"], body["distinct_reporters"]) == (3, 1)
    assert body["verdict"] == "SUSPICIOUS"
    assert body["display_value"] == "98XXXXX210"


@pytest.mark.parametrize(
    ("kind", "value", "query"),
    [
        ("phone", "1930", "1930"),
        ("phone", "1800 1600", "18001600"),
        ("phone", "+91 80 4100 2233", "08041002233"),
        ("sender_id", "VM-HDFCBK", "HDFCBK"),
        ("upi", "freshbakes@okaxis", "FreshBakes@OkAxis"),
        ("url", "https://cybercrime.gov.in/", "cybercrime.gov.in"),
    ],
)
def test_verified_values_stay_verified_under_attack(
    client: TestClient, kind: str, value: str, query: str
) -> None:
    for n in range(1, 6):
        report(client, **by(n), identifier_type=kind, identifier_value=value)
    body = lookup(client, kind, query).json()
    assert body["verdict"] == "VERIFIED_BUSINESS"
    assert body["report_count"] == 5


@pytest.mark.parametrize(
    "changes",
    [
        {"identifier_value": "12345"},
        {"identifier_value": "test"},
        {"identifier_value": ""},
        {"identifier_type": "upi", "identifier_value": "+91 98765 43210"},
        {"pincode": "999999"},
        {"pincode": "HSR"},
        {"occurred_at": "2026-11-05T10:00:00+05:30"},
        {"occurred_at": "2026-10-27T18:21:04"},
        {"occurred_at": "yesterday"},
        {"occurred_at": ""},
    ],
)
def test_invalid_reports_are_400_and_store_nothing(
    client: TestClient, changes: dict[str, Any]
) -> None:
    response = report(client, **changes)
    assert response.status_code == 400
    assert "error" in response.json()
    assert lookup(client, "phone", "+919876543210").json()["verdict"] == "NO_REPORTS"


def test_unknown_scam_type_is_stored_as_other(client: TestClient) -> None:
    report(client, scam_type="crypto-doubler")
    assert lookup(client, "phone", "+919876543210").json()["scam_type"] == "other"


def test_unknown_channel_is_stored_as_something_else(client: TestClient) -> None:
    report(client, channel="Carrier pigeon")
    body = lookup(client, "phone", "+919876543210").json()
    assert body["evidence"][0]["channel"] == "Something else"


def test_offsets_compare_as_instants(client: TestClient) -> None:
    report(client, **by(1), occurred_at="2026-10-27T12:51:04Z")
    report(client, **by(2), occurred_at="2026-10-27T07:51:04-05:00")
    body = lookup(client, "phone", "+919876543210").json()
    assert body["first_seen"] == body["last_seen"] == "2026-10-27T18:21:04+05:30"


def test_report_without_ip_prefix_uses_the_connection(client: TestClient) -> None:
    sent = {k: v for k, v in REPORT.items() if k != "ip_prefix"}
    assert client.post("/reports", json=sent).status_code == 201


def test_reset_deletes_every_report(client: TestClient) -> None:
    for n in (1, 2, 3):
        report(client, **by(n))
    assert client.post("/admin/reset").status_code == 200
    body = lookup(client, "phone", "+919876543210").json()
    assert body["verdict"] == "NO_REPORTS"
    assert body["report_count"] == 0
    second = report(client, **by(4)).json()
    assert second["merged"] is False


def test_database_holds_no_raw_identifier_reporter_or_note(
    client: TestClient, db_path: Path
) -> None:
    sent = REPORT | by(1)
    report(client, **by(1))
    client.post("/admin/reset")
    report(client, **by(1))
    raw = b"".join(p.read_bytes() for p in db_path.parent.glob(db_path.name + "*"))
    for secret in [
        "9876543210",
        sent["reporter_id"],
        sent["ip_prefix"],
        sent["note"],
        "police",
    ]:
        assert secret.encode() not in raw, secret


def test_times_are_shown_to_the_second(client: TestClient) -> None:
    report(client, occurred_at="2026-10-27T18:21:04.907913+05:30")
    body = lookup(client, "phone", "+919876543210").json()
    assert body["first_seen"] == "2026-10-27T18:21:04+05:30"
    assert body["evidence"][0]["occurred_at"] == "2026-10-27T18:21:04+05:30"
