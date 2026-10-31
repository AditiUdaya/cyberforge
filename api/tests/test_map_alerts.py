"""GET /map, GET /alerts and POST /challenges (task B6), on an injected clock.

Owner: B. Filled in by: B6.
"""

from __future__ import annotations

from datetime import timedelta
from itertools import count
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.areas import areas, distance_km
from tests.conftest import START

HSR, BTM, KORAMANGALA, BANDRA = "560102", "560076", "560034", "400050"
_ids = count(1)


def report(c: TestClient, pincode: str, hours_ago: float, scam_type: str = "job-offer") -> None:
    """A counted report: a new person, connection and number, in their own words."""
    n = next(_ids)
    occurred = START - timedelta(hours=hours_ago)
    body: dict[str, Any] = {
        "report_id": f"rep_{n}",
        "occurred_at": occurred.isoformat(),
        "reported_at": (occurred + timedelta(minutes=10)).isoformat(),
        "reporter_id": f"r_{n}",
        "ip_prefix": f"10.{n % 250}.{n // 250}",
        "channel": "Phone call",
        "scam_type": scam_type,
        "identifier_type": "phone",
        "identifier_value": f"9{n:09d}",
        "pincode": pincode,
        "note": f"Story {n}: the caller {n * 7919} talked about thing {n * 31337} for a while.",
    }
    assert c.post("/reports", json=body).status_code == 201


def clusters(c: TestClient, pincode: str, **params: float) -> dict[str, dict[str, Any]]:
    response = c.get("/map", params={"pincode": pincode, **{k: str(v) for k, v in params.items()}})
    assert response.status_code == 200, response.text
    return {x["pincode"]: x for x in response.json()["clusters"]}


def alerts(c: TestClient, pincode: str) -> list[dict[str, Any]]:
    response = c.get("/alerts", params={"pincode": pincode})
    assert response.status_code == 200, response.text
    found: list[dict[str, Any]] = response.json()["alerts"]
    return found


# ---------------------------------------------------------------- map


def test_map_window_keeps_only_recent_reports(client: TestClient) -> None:
    for days in (6, 8, 30, 45):
        report(client, HSR, days * 24 + 2)
    assert clusters(client, HSR, radius_km=0)[HSR]["count"] == 1
    assert clusters(client, HSR, days=31, radius_km=0)[HSR]["count"] == 3


def test_map_defaults_are_7_days_and_2_km(client: TestClient) -> None:
    report(client, HSR, 24)
    near = [p for p in areas() if p != HSR and distance_km(HSR, p) <= 2]
    far = [p for p in areas() if distance_km(HSR, p) > 2]
    for p in near + far[:3]:
        report(client, p, 24)
    assert set(clusters(client, HSR)) == {HSR, *near}


def test_radius_edge_is_exact(client: TestClient) -> None:
    d = distance_km(HSR, KORAMANGALA)
    report(client, HSR, 5)
    report(client, KORAMANGALA, 5)
    assert KORAMANGALA in clusters(client, HSR, radius_km=d + 0.05)
    assert KORAMANGALA not in clusters(client, HSR, radius_km=d - 0.05)


def test_clusters_sit_at_appendix_b_points_with_severity(client: TestClient) -> None:
    for _ in range(12):
        report(client, HSR, 30, "digital-arrest")
    report(client, HSR, 30, "job-offer")
    cluster = clusters(client, HSR)[HSR]
    assert (cluster["lat"], cluster["lng"]) == (12.9116, 77.6473)
    assert (cluster["locality"], cluster["city"]) == ("HSR Layout", "Bengaluru")
    assert cluster["count"] == 13
    assert cluster["top_scam_type"] == "digital-arrest"
    assert cluster["severity"] == "CRIT"


@pytest.mark.parametrize(("n", "severity"), [(1, "MED"), (4, "MED"), (5, "HIGH"), (10, "CRIT")])
def test_severity_bands(client: TestClient, n: int, severity: str) -> None:
    for _ in range(n):
        report(client, BTM, 10)
    assert clusters(client, BTM, radius_km=0)[BTM]["severity"] == severity


def test_other_cities_never_appear(client: TestClient) -> None:
    report(client, BANDRA, 10)
    assert BANDRA not in clusters(client, HSR, radius_km=50)


def test_fakes_never_reach_the_map(client: TestClient) -> None:
    for n in range(40):
        body = {
            "report_id": f"bomb_{n}",
            "occurred_at": (START - timedelta(hours=3, minutes=n % 10)).isoformat(),
            "reported_at": (START - timedelta(hours=2, minutes=-n)).isoformat(),
            "reporter_id": f"friend_{n}",
            "ip_prefix": "103.21.58",
            "channel": "Phone call",
            "scam_type": "fake-customer-care",
            "identifier_type": "phone",
            "identifier_value": "+91 80 4555 0123",
            "pincode": HSR,
            "note": "",
        }
        assert client.post("/reports", json=body).status_code == 201
    assert clusters(client, HSR) == {}
    assert alerts(client, HSR) == []


@pytest.mark.parametrize("params", [{}, {"pincode": "999999"}, {"pincode": "560102", "days": "0"}])
def test_bad_map_queries_are_400(client: TestClient, params: dict[str, str]) -> None:
    response = client.get("/map", params=params)
    assert response.status_code == 400
    assert "error" in response.json()


# ---------------------------------------------------------------- alerts


def steady(c: TestClient, pincode: str, per_day: int, scam_type: str = "job-offer") -> None:
    for day in range(7):
        for k in range(per_day):
            report(c, pincode, 24 + 24 * day + 2 + 3 * k, scam_type)


def today(c: TestClient, pincode: str, n: int, scam_type: str = "job-offer") -> None:
    for k in range(n):
        report(c, pincode, 1 + 2 * k, scam_type)


def test_spike_when_double_the_baseline_and_at_least_five(client: TestClient) -> None:
    steady(client, HSR, 2)
    today(client, HSR, 10)
    assert alerts(client, HSR) == [
        {"type": "SPIKE", "pincode": HSR, "window": "24h", "count": 10, "baseline_per_day": 2.0}
    ]


def test_exactly_double_with_six_is_a_spike(client: TestClient) -> None:
    steady(client, HSR, 3)
    today(client, HSR, 6)
    assert [a["type"] for a in alerts(client, HSR)] == ["SPIKE"]


def test_double_but_only_four_is_quiet(client: TestClient) -> None:
    steady(client, HSR, 2)
    today(client, HSR, 4)
    assert alerts(client, HSR) == []


def test_steady_area_is_quiet(client: TestClient) -> None:
    steady(client, HSR, 2)
    today(client, HSR, 2)
    assert alerts(client, HSR) == []


def test_new_type_in_the_last_day(client: TestClient) -> None:
    steady(client, HSR, 1, "job-offer")
    today(client, HSR, 1, "sextortion")
    assert alerts(client, HSR) == [
        {"type": "NEW_TYPE", "pincode": HSR, "scam_type": "sextortion", "window": "24h"}
    ]


def test_type_seen_29_days_ago_is_not_new(client: TestClient) -> None:
    report(client, HSR, 29 * 24, "sextortion")
    today(client, HSR, 1, "sextortion")
    assert alerts(client, HSR) == []


def test_type_seen_31_days_ago_is_new_again(client: TestClient) -> None:
    report(client, HSR, 31.5 * 24, "sextortion")
    today(client, HSR, 1, "sextortion")
    assert [a["type"] for a in alerts(client, HSR)] == ["NEW_TYPE"]


def test_unknown_area_alerts_are_400(client: TestClient) -> None:
    assert client.get("/alerts", params={"pincode": "999999"}).status_code == 400


# ---------------------------------------------------------------- challenges

CHALLENGE = {
    "identifier_type": "phone",
    "identifier_value": "+91 80 4555 0123",
    "claimant_name": "Fresh Bakes",
    "contact_email": "owner@example.com",
    "proof_note": "GST certificate and shop licence attached.",
}


def known_scam(c: TestClient) -> None:
    for n in range(5):
        body = {
            "report_id": f"real_{n}",
            "occurred_at": (START - timedelta(days=n + 1)).isoformat(),
            "reporter_id": f"real_{n}",
            "ip_prefix": f"49.{n}.1",
            "channel": "Phone call",
            "scam_type": "fake-customer-care",
            "identifier_type": "phone",
            "identifier_value": "08045550123",
            "pincode": HSR,
            "note": f"Person {n} wrote this in their own way, number {n * 7919} and day {n * 13}.",
        }
        assert c.post("/reports", json=body).status_code == 201


def lookup(c: TestClient) -> dict[str, Any]:
    params = {"type": "phone", "value": "+918045550123"}
    result: dict[str, Any] = c.get("/lookup", params=params).json()
    return result


def test_challenge_marks_the_number_and_caps_the_verdict(client: TestClient) -> None:
    known_scam(client)
    assert lookup(client)["verdict"] == "KNOWN_SCAM"
    response = client.post("/challenges", json=CHALLENGE)
    assert response.status_code == 201
    assert response.json()["status"] == "under_review"
    body = lookup(client)
    assert (body["challenged"], body["verdict"]) == (True, "SUSPICIOUS")


def test_challenge_before_any_report_still_holds(client: TestClient) -> None:
    client.post("/challenges", json=CHALLENGE)
    known_scam(client)
    body = lookup(client)
    assert (body["challenged"], body["verdict"]) == (True, "SUSPICIOUS")


def test_claimant_contact_is_never_returned(client: TestClient) -> None:
    known_scam(client)
    replies = [client.post("/challenges", json=CHALLENGE).text, str(lookup(client))]
    for reply in replies:
        assert "owner@example.com" not in reply
        assert "Fresh Bakes" not in reply


def test_invalid_challenge_identifier_is_400(client: TestClient) -> None:
    response = client.post("/challenges", json=CHALLENGE | {"identifier_value": "12345"})
    assert response.status_code == 400


def test_reset_clears_challenges(client: TestClient) -> None:
    client.post("/challenges", json=CHALLENGE)
    client.post("/admin/reset")
    assert lookup(client)["challenged"] is False
