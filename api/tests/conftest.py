"""Shared fixtures: in-process app, temporary database, injectable clock, test licence keys.

Owner: B. Filled in by: B0.
"""

from __future__ import annotations

import base64
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.clock import FixedClock
from app.license.verify import canonical_bytes
from app.main import create_app

START = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
TEST_HMAC_KEY = "test-hmac-key-not-a-secret"

# A throwaway key pair made fresh for each test run; nothing is written to disk.
SIGNING_KEY = Ed25519PrivateKey.generate()
PUBLIC_PEM = SIGNING_KEY.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
)

LicenceMaker = Callable[..., dict[str, Any]]


def sign_licence(
    licensee: str, expires_at: str, key: Ed25519PrivateKey = SIGNING_KEY
) -> dict[str, Any]:
    signature = key.sign(canonical_bytes(licensee, expires_at))
    return {
        "licensee": licensee,
        "expires_at": expires_at,
        "signature": base64.b64encode(signature).decode(),
    }


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(START)


@pytest.fixture
def licence(clock: FixedClock) -> LicenceMaker:
    """make(minutes=5) signs a licence that expires that long after the clock's now."""

    def make(licensee: str = "Demo Bank", **delta: float) -> dict[str, Any]:
        expires = clock.now() + timedelta(**delta)
        return sign_licence(licensee, expires.isoformat())

    return make


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.sqlite"


@pytest.fixture
def make_app(db_path: Path, clock: FixedClock) -> Callable[[], FastAPI]:
    """A fresh app on the same database and clock: calling it again is a restart."""

    def make() -> FastAPI:
        return create_app(
            db_path=db_path, clock=clock, hmac_key=TEST_HMAC_KEY, public_key_pem=PUBLIC_PEM
        )

    return make


@pytest.fixture
def app(make_app: Callable[[], FastAPI]) -> FastAPI:
    return make_app()


@pytest.fixture
def bare_client(app: FastAPI) -> Iterator[TestClient]:
    """A client for a server with no licence loaded yet."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(bare_client: TestClient, licence: LicenceMaker) -> TestClient:
    """A client for a server with a one-year licence loaded."""
    response = bare_client.post("/license", json=licence(days=365))
    assert response.status_code == 200, response.text
    return bare_client
