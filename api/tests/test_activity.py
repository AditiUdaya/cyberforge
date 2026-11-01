"""The activity feed behind the website's live panel: every event, grouped, masked, never personal.

Owner: B. Filled in by: B9.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.clock import FixedClock
from tests.conftest import START

NUMBER = "+91 98765 43210"


def body(n: int, **changes: Any) -> dict[str, Any]:
    return {
        "report_id": f"rep_{n}",
        "occurred_at": (START - timedelta(days=1 + n % 20, minutes=n)).isoformat(),
        "reporter_id": f"r_{n}",
        "ip_prefix": f"10.{n}.1",
        "channel": "Phone call",
        "scam_type": "digital-arrest",
        "identifier_type": "phone",
        "identifier_value": NUMBER,
        "pincode": "560102",
        "note": f"Person {n} in their own words, story {n * 7919}, detail {n * 31337} here.",
    } | changes


def activity(c: TestClient) -> dict[str, Any]:
    response = c.get("/app/activity")
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


def kinds(c: TestClient) -> list[str]:
    return [e["kind"] for e in activity(c)["events"]]


def test_a_counted_report_appears_masked_with_area_and_type(client: TestClient) -> None:
    client.post("/reports", json=body(1))
    [event] = activity(client)["events"]
    assert event["kind"] == "report"
    assert event["display"] == "98XXXXX210"
    assert (event["locality"], event["scam_type"], event["channel"]) == (
        "HSR Layout",
        "digital-arrest",
        "Phone call",
    )
    assert event["count"] == 1


def test_repeats_from_one_person_are_grouped(client: TestClient) -> None:
    for n in range(3):
        client.post("/reports", json=body(n, reporter_id="r_same", report_id=f"x{n}"))
    events = activity(client)["events"]
    merged = [e for e in events if e["kind"] == "merged"]
    assert len(merged) == 1 and merged[0]["count"] == 2


def test_a_coordinated_burst_shows_as_one_growing_line(client: TestClient) -> None:
    for n in range(40):
        bomb = body(
            n,
            identifier_value="+91 80 4555 0123",
            ip_prefix="103.21.58",
            note="",
            occurred_at=(START - timedelta(hours=3, minutes=n % 10)).isoformat(),
            reported_at=(START - timedelta(hours=2, minutes=-n)).isoformat(),
        )
        assert client.post("/reports", json=bomb).status_code == 201
    bursts = [e for e in activity(client)["events"] if e["kind"] == "burst"]
    assert len(bursts) == 1
    assert bursts[0]["count"] == 40
    assert bursts[0]["display"] == "80XXXXX123"


def test_junk_is_shown_with_the_reason_but_never_the_value(client: TestClient) -> None:
    client.post("/reports", json=body(1, identifier_value="12345"))
    client.post("/reports", json=body(2, identifier_value="test"))
    client.post("/reports", json=body(3, pincode="999999"))
    events = activity(client)["events"]
    rejected = {e["detail"]: e["count"] for e in events if e["kind"] == "rejected"}
    assert rejected == {"invalid phone": 2, "unknown area": 1}
    text = str(events)
    assert "12345" not in text and "test" not in text and "999999" not in text


def test_rate_limited_reporters_are_shown(client: TestClient) -> None:
    for n in range(5):
        client.post(
            "/reports",
            json=body(
                n,
                reporter_id="r_spam",
                report_id=f"s{n}",
                reported_at=(START - timedelta(minutes=50 - n)).isoformat(),
            ),
        )
    limited = [e for e in activity(client)["events"] if e["kind"] == "rate_limited"]
    assert len(limited) == 1 and limited[0]["count"] == 2


def test_becoming_a_known_scam_is_announced_once(client: TestClient) -> None:
    for n in range(5):
        client.post("/reports", json=body(n))
    assert kinds(client).count("known_scam") == 1


def test_alerts_are_announced_once_and_listed_live(client: TestClient) -> None:
    for n in range(6):
        client.post(
            "/reports",
            json=body(
                n,
                identifier_value=f"9{n:09d}",
                occurred_at=(START - timedelta(hours=1 + n)).isoformat(),
            ),
        )
    result = activity(client)
    alert_events = [e for e in result["events"] if e["kind"] == "alert"]
    assert [e["detail"] for e in alert_events].count("SPIKE") == 1
    assert {(a["type"], a["pincode"]) for a in result["alerts"]} >= {("SPIKE", "560102")}


def test_disputes_are_shown_without_contact_details(client: TestClient) -> None:
    challenge = {
        "identifier_type": "phone",
        "identifier_value": NUMBER,
        "claimant_name": "Fresh Bakes",
        "contact_email": "owner@example.com",
        "proof_note": "GST certificate",
    }
    client.post("/challenges", json=challenge)
    events = activity(client)["events"]
    assert [e["kind"] for e in events] == ["dispute"]
    assert "Fresh Bakes" not in str(events) and "owner@example.com" not in str(events)


def test_newest_first_and_reset_clears_the_feed(client: TestClient) -> None:
    client.post("/reports", json=body(1))
    client.post("/reports", json=body(2, identifier_value="12345"))
    assert kinds(client)[0] == "rejected"
    client.post("/admin/reset")
    assert activity(client) == {"events": [], "alerts": []}


def test_feed_is_behind_the_licence(bare_client: TestClient) -> None:
    response = bare_client.get("/app/activity")
    assert (response.status_code, response.json()) == (403, {"error": "LICENSE_EXPIRED"})


def test_events_never_hold_a_raw_number_or_reporter_field(
    client: TestClient, db_path: Path
) -> None:
    for n in range(5):
        client.post("/reports", json=body(n))
    raw = b"".join(p.read_bytes() for p in db_path.parent.glob(db_path.name + "*"))
    for secret in ("9876543210", "r_1", "10.1.1", "own words"):
        assert secret.encode() not in raw, secret


def test_reports_older_than_30_days_are_accepted_but_never_shown(client: TestClient) -> None:
    old = (START - timedelta(days=45)).isoformat()
    for n in range(6):
        sent = body(n, identifier_value=f"9{n:09d}", occurred_at=old)
        assert client.post("/reports", json=sent).status_code == 201
    looked_up = client.get("/lookup", params={"type": "phone", "value": "9000000000"}).json()
    assert looked_up["report_count"] == 1
    assert activity(client) == {"events": [], "alerts": []}


def test_a_29_day_old_report_is_shown_then_ages_out(client: TestClient, clock: FixedClock) -> None:
    client.post("/reports", json=body(1, occurred_at=(START - timedelta(days=29)).isoformat()))
    assert kinds(client) == ["report"]
    clock.advance(timedelta(days=2))
    assert activity(client) == {"events": [], "alerts": []}


def test_old_junk_and_rate_limits_are_not_shown(client: TestClient) -> None:
    old = (START - timedelta(days=45)).isoformat()
    client.post("/reports", json=body(1, occurred_at=old, pincode="999999"))
    for n in range(5):
        client.post(
            "/reports", json=body(n, reporter_id="r_spam", report_id=f"s{n}", occurred_at=old)
        )
    assert activity(client)["events"] == []


def test_a_burst_of_old_reports_is_not_shown(client: TestClient) -> None:
    old = (START - timedelta(days=40)).isoformat()
    for n in range(20):
        client.post(
            "/reports",
            json=body(
                n, identifier_value="+91 80 4555 0123", ip_prefix="1.2.3", note="", occurred_at=old
            ),
        )
    assert activity(client)["events"] == []


def test_recent_reports_still_show_beside_old_ones(client: TestClient) -> None:
    client.post("/reports", json=body(1, occurred_at=(START - timedelta(days=45)).isoformat()))
    client.post("/reports", json=body(2, identifier_value="+91 91234 56780"))
    events = activity(client)["events"]
    assert [e["display"] for e in events] == ["91XXXXX780"]
