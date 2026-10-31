"""Keyed HMACs and connection prefixes; licence key loading edge cases.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.identity import HMAC_KEY_ENV, Keyring, connection_prefix
from app.license.verify import DEFAULT_PUBLIC_KEY, PUBLIC_KEY_ENV, load_public_key
from app.main import create_app
from tests.conftest import TEST_HMAC_KEY, LicenceMaker


def test_digests_are_keyed_and_separated_by_purpose() -> None:
    a, b = Keyring("a" * 32), Keyring("b" * 32)
    assert a.reporter("r_1") != b.reporter("r_1")
    assert a.reporter("r_1") != a.ip_prefix("r_1")
    assert a.identifier("phone", "+919876543210") != a.identifier("upi", "+919876543210")
    assert a.reporter(" r_1 ") == a.reporter("r_1")
    assert "r_1" not in a.reporter("r_1")


def test_short_or_missing_key_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="at least"):
        Keyring("short")
    monkeypatch.delenv(HMAC_KEY_ENV, raising=False)
    with pytest.raises(RuntimeError, match=HMAC_KEY_ENV):
        Keyring.from_env()
    monkeypatch.setenv(HMAC_KEY_ENV, TEST_HMAC_KEY)
    assert Keyring.from_env().reporter("x") == Keyring(TEST_HMAC_KEY).reporter("x")


@pytest.mark.parametrize(
    ("host", "prefix"),
    [
        ("103.21.58.77", "103.21.58.0"),
        ("2001:db8:abcd:12::1", "2001:db8:abcd::"),
        ("testclient", "unknown"),
        (None, "unknown"),
        ("", "unknown"),
    ],
)
def test_connection_prefix_drops_the_host_part(host: str | None, prefix: str) -> None:
    assert connection_prefix(host) == prefix


def test_placeholder_public_key_loads_as_none() -> None:
    assert load_public_key(b"PLACEHOLDER: no key yet.") is None
    assert DEFAULT_PUBLIC_KEY.name == "public_key.pem"


def test_missing_key_file_and_non_ed25519_keys_load_as_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(PUBLIC_KEY_ENV, str(tmp_path / "absent.pem"))
    assert load_public_key() is None
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    other = ec.generate_private_key(ec.SECP256R1()).public_key()
    pem = other.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    assert load_public_key(pem) is None


def test_server_without_a_public_key_refuses_every_licence(
    tmp_path: Path, licence: LicenceMaker
) -> None:
    app = create_app(
        db_path=tmp_path / "x.sqlite", hmac_key=TEST_HMAC_KEY, public_key_pem=b"PLACEHOLDER"
    )
    with TestClient(app) as c:
        response = c.post("/license", json=licence(days=30))
        assert response.status_code == 400
        assert "public key" in response.json()["error"]
        assert c.get("/health").status_code == 200
