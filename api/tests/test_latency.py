"""In-process latency (SPEC test layer 7): lookup p95 under 20 ms with thousands of reports loaded.

Over HTTPS the target is p95 under 300 ms; that is judge/perf.py against the deployed address.

Owner: B. Filled in by: B8.
"""

from __future__ import annotations

import random
import time
from datetime import timedelta
from statistics import quantiles

from fastapi.testclient import TestClient

from tests.conftest import START

REPORTS = 3000
NUMBERS = 600
LOOKUPS = 500
P95_MS = 20.0
AREAS = ["560102", "560038", "560034", "560066", "560076", "400050", "110016"]


def p95(samples: list[float]) -> float:
    return quantiles(samples, n=100)[94]


def test_lookup_and_map_stay_fast_with_thousands_of_reports(client: TestClient) -> None:
    rng = random.Random(8)
    numbers = [f"9{n:09d}" for n in range(1, NUMBERS + 1)]
    for n in range(REPORTS):
        occurred = START - timedelta(minutes=rng.randint(60, 60 * 24 * 30))
        body = {
            "report_id": f"rep_{n}",
            "occurred_at": occurred.isoformat(),
            "reported_at": (occurred + timedelta(minutes=rng.randint(5, 300))).isoformat(),
            "reporter_id": f"r_{n}",
            "ip_prefix": f"{rng.randint(1, 223)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}",
            "channel": "Phone call",
            "scam_type": rng.choice(["digital-arrest", "job-offer", "otp-call"]),
            "identifier_type": "phone",
            "identifier_value": rng.choice(numbers),
            "pincode": rng.choice(AREAS),
            "note": f"Report {n}: caller {rng.randint(1, 10**9)} said {rng.randint(1, 10**9)}.",
        }
        assert client.post("/reports", json=body).status_code == 201

    lookups = []
    for _ in range(LOOKUPS):
        value = rng.choice(numbers) if rng.random() < 0.8 else f"8{rng.randint(10**8, 10**9 - 1)}"
        started = time.perf_counter()
        response = client.get("/lookup", params={"type": "phone", "value": value})
        lookups.append((time.perf_counter() - started) * 1000)
        assert response.status_code == 200

    maps = []
    for _ in range(50):
        started = time.perf_counter()
        client.get("/map", params={"pincode": rng.choice(AREAS), "days": "30", "radius_km": "10"})
        maps.append((time.perf_counter() - started) * 1000)

    assert p95(lookups) < P95_MS, f"lookup p95 {p95(lookups):.1f} ms"
    assert p95(maps) < 5 * P95_MS, f"map p95 {p95(maps):.1f} ms"
