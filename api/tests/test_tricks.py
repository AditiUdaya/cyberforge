"""The PRD's four tricks through the API, and the real campaign they must not block (task B5).

Owner: B. Filled in by: B5.
"""

from __future__ import annotations

from datetime import UTC, timedelta
from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import START

BAKERY = "+91 80 4555 0123"
STORIES = [
    "My father got a video call from a man in police uniform about a parcel with drugs.",
    "A lady said my KYC expired and sent a link that looked exactly like the bank site.",
    "Caller offered a work from home job and asked for a deposit of five thousand first.",
    "They said my electricity would be cut tonight unless I paid on a strange UPI ID.",
    "Got a message about a lottery car prize, then a call asking for a processing fee.",
    "Someone claiming to be customer care asked me to install a screen sharing app.",
]


def at(minutes: float) -> str:
    return (START - timedelta(minutes=minutes)).astimezone(UTC).isoformat()


def body(n: int, **changes: Any) -> dict[str, Any]:
    return {
        "report_id": f"rep_{n}",
        "occurred_at": at(600 + 37 * n),
        "reported_at": at(300 + 37 * n),
        "reporter_id": f"r_{n}",
        "ip_prefix": f"10.{n}.1",
        "channel": "Phone call",
        "scam_type": "digital-arrest",
        "identifier_type": "phone",
        "identifier_value": BAKERY,
        "pincode": "560038",
        "note": STORIES[n % len(STORIES)] + f" It happened on day {n}.",
    } | changes


def lookup(c: TestClient) -> dict[str, Any]:
    result: dict[str, Any] = c.get("/lookup", params={"type": "phone", "value": BAKERY}).json()
    return result


def test_report_bombing_by_40_friends_is_not_a_known_scam(client: TestClient) -> None:
    script = "This bakery cheated me, they took money and never delivered the cake. Fraud shop!"
    for n in range(40):
        sent = body(
            n,
            note=script,
            occurred_at=at(90 + n % 12),
            reported_at=at(70 - n * 1.2),
        )
        assert client.post("/reports", json=sent).status_code == 201
    result = lookup(client)
    assert result["verdict"] == "SUSPICIOUS"
    assert result["distinct_reporters"] == 1
    assert result["display_value"] == "80XXXXX123"


def test_22_accounts_on_one_wifi_count_as_one(client: TestClient) -> None:
    for n in range(22):
        sent = body(n, ip_prefix="103.21.58", reported_at=at(200 - 5 * n))
        assert client.post("/reports", json=sent).status_code == 201
    result = lookup(client)
    assert result["distinct_reporters"] == 1
    assert result["verdict"] == "SUSPICIOUS"


def test_one_person_six_times_in_an_hour_gets_429_after_three(client: TestClient) -> None:
    statuses = []
    for n in range(6):
        sent = body(n, reporter_id="r_spammer", reported_at=at(60 - 10 * n))
        response = client.post("/reports", json=sent)
        statuses.append(response.status_code)
        if response.status_code == 429:
            assert "error" in response.json()
    assert statuses == [201, 201, 201, 429, 429, 429]
    result = lookup(client)
    assert (result["report_count"], result["distinct_reporters"]) == (3, 1)


def test_the_same_person_on_different_days_is_not_rate_limited(client: TestClient) -> None:
    for n in range(6):
        sent = body(n, reporter_id="r_regular", reported_at=at(60 * 24 * n + 30))
        assert client.post("/reports", json=sent).status_code == 201
    assert lookup(client)["distinct_reporters"] == 1


def test_real_campaign_from_unrelated_people_is_a_known_scam(client: TestClient) -> None:
    for n in range(6):
        assert client.post("/reports", json=body(n)).status_code == 201
    result = lookup(client)
    assert result["verdict"] == "KNOWN_SCAM"
    assert result["distinct_reporters"] == 6
    assert result["display_value"] == "+918045550123"


def test_reported_at_from_the_future_is_clamped_not_trusted(client: TestClient) -> None:
    future = (START + timedelta(days=3)).isoformat()
    for n in range(4):
        sent = body(n, reporter_id="r_tricky", reported_at=future)
        status = client.post("/reports", json=sent).status_code
        assert status == (201 if n < 3 else 429)


def test_bad_reported_at_falls_back_to_server_time(client: TestClient) -> None:
    assert client.post("/reports", json=body(1, reported_at="soon")).status_code == 201
    assert lookup(client)["report_count"] == 1
