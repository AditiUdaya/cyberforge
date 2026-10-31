"""GET /health: always 200 {"ok": true} (PRD Appendix A route 1).

Owner: B. Filled in by: B0.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_health_is_json(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers["content-type"].startswith("application/json")


def test_health_rejects_post(client: TestClient) -> None:
    assert client.post("/health").status_code == 405


def test_root_describes_the_api(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "GET /lookup?type=&value=" in body["routes"]


def test_root_is_behind_the_licence_gate(bare_client: TestClient) -> None:
    response = bare_client.get("/")
    assert (response.status_code, response.json()) == (403, {"error": "LICENSE_EXPIRED"})
