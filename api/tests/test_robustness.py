"""Robustness (SPEC test layer 10): fuzzed bodies and queries never crash the server, concurrent
reports on one identifier are counted exactly, and reset leaves an empty state.

Owner: B. Filled in by: B7.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.conftest import START

FIELDS = [
    "report_id",
    "occurred_at",
    "reported_at",
    "reporter_id",
    "ip_prefix",
    "channel",
    "scam_type",
    "identifier_type",
    "identifier_value",
    "pincode",
    "locality",
    "city",
    "note",
    "has_screenshot",
    "amount_lost_inr",
]
GOOD: dict[str, Any] = {
    "report_id": "rep_1",
    "occurred_at": (START - timedelta(hours=2)).isoformat(),
    "reporter_id": "r_1",
    "ip_prefix": "103.21.58",
    "channel": "Phone call",
    "scam_type": "digital-arrest",
    "identifier_type": "phone",
    "identifier_value": "+91 98765 43210",
    "pincode": "560102",
    "note": "A man in police uniform asked for money on a video call.",
}

json_values = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=40),
    lambda children: (
        st.lists(children, max_size=3) | st.dictionaries(st.text(max_size=8), children, max_size=3)
    ),
    max_leaves=6,
)
FUZZ = settings(
    max_examples=300, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)


def assert_clean(response: Any) -> None:
    assert response.status_code < 500, response.text
    body = response.json()
    if response.status_code >= 400:
        assert isinstance(body.get("error"), str) and body["error"]


@FUZZ
@given(st.dictionaries(st.sampled_from(FIELDS), json_values, max_size=len(FIELDS)))
def test_fuzzed_report_bodies_never_crash(client: TestClient, body: dict[str, Any]) -> None:
    assert_clean(client.post("/reports", json=body))


@FUZZ
@given(st.sampled_from(FIELDS), json_values)
def test_one_bad_field_in_a_good_report_never_crashes(
    client: TestClient, field: str, value: Any
) -> None:
    assert_clean(client.post("/reports", json=GOOD | {field: value}))


@FUZZ
@given(st.binary(max_size=200))
def test_raw_bytes_never_crash(client: TestClient, raw: bytes) -> None:
    headers = {"content-type": "application/json"}
    assert_clean(client.post("/reports", content=raw, headers=headers))


@FUZZ
@given(st.text(max_size=30), st.text(max_size=80))
def test_fuzzed_lookups_never_crash(client: TestClient, kind: str, value: str) -> None:
    assert_clean(client.get("/lookup", params={"type": kind, "value": value}))


@FUZZ
@given(st.text(max_size=12), st.text(max_size=12), st.text(max_size=12))
def test_fuzzed_map_and_alert_queries_never_crash(
    client: TestClient, pincode: str, days: str, radius: str
) -> None:
    assert_clean(client.get("/map", params={"pincode": pincode, "days": days, "radius_km": radius}))
    assert_clean(client.get("/alerts", params={"pincode": pincode}))


def test_50_concurrent_reports_on_one_identifier_are_counted_exactly(client: TestClient) -> None:
    def send(n: int) -> int:
        body = GOOD | {
            "report_id": f"rep_{n}",
            "reporter_id": f"r_{n}",
            "ip_prefix": f"10.{n}.1",
            "occurred_at": (START - timedelta(days=1 + n % 20, minutes=n)).isoformat(),
            "note": f"Person {n} in their own words, story {n * 7919}, detail {n * 31337}.",
        }
        return client.post("/reports", json=body).status_code

    with ThreadPoolExecutor(max_workers=16) as pool:
        statuses = list(pool.map(send, range(50)))
    assert statuses == [201] * 50
    body = client.get("/lookup", params={"type": "phone", "value": "9876543210"}).json()
    assert body["report_count"] == 50


def test_reset_then_everything_is_empty(client: TestClient) -> None:
    client.post("/reports", json=GOOD)
    client.post("/admin/reset")
    assert (
        client.get("/lookup", params={"type": "phone", "value": "9876543210"}).json()["verdict"]
        == "NO_REPORTS"
    )
    assert client.get("/map", params={"pincode": "560102", "days": "30"}).json() == {"clusters": []}
    assert client.get("/alerts", params={"pincode": "560102"}).json() == {"alerts": []}
    assert client.get("/license").json()["valid"] is True
