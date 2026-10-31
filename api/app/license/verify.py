"""Ed25519 signature check over canonical JSON of licensee and expires_at,
with the built-in public key.

Format: {"licensee", "expires_at", "signature"}. The signature is Ed25519 over the canonical JSON
of the other two fields (sorted keys, no spaces, UTF-8), base64-encoded.

Owner: B. Filled in by: B3.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PUBLIC_KEY_ENV = "SCAM_MAP_LICENSE_PUBLIC_KEY"
DEFAULT_PUBLIC_KEY = Path(__file__).resolve().parent / "public_key.pem"


class InvalidLicence(ValueError):
    """The licence file is malformed, unsigned, signed by another key, or edited."""


@dataclass(frozen=True)
class Licence:
    licensee: str
    expires_at_text: str
    expires_at: datetime
    signature: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "licensee": self.licensee,
                "expires_at": self.expires_at_text,
                "signature": self.signature,
            }
        )


def canonical_bytes(licensee: str, expires_at: str) -> bytes:
    """The exact bytes that are signed. scripts/license_sign.py signs these too."""
    doc = {"licensee": licensee, "expires_at": expires_at}
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def load_public_key(pem: bytes | None = None) -> Ed25519PublicKey | None:
    """The configured public key, or None while public_key.pem is still the placeholder."""
    if pem is None:
        path = Path(os.environ.get(PUBLIC_KEY_ENV, str(DEFAULT_PUBLIC_KEY)))
        if not path.exists():
            return None
        pem = path.read_bytes()
    try:
        key = serialization.load_pem_public_key(pem)
    except ValueError:
        return None
    return key if isinstance(key, Ed25519PublicKey) else None


def verify(doc: dict[str, Any], key: Ed25519PublicKey | None) -> Licence:
    if key is None:
        raise InvalidLicence("no licence public key is configured on this server")
    licensee, expires_at, signature = (doc.get(f) for f in ("licensee", "expires_at", "signature"))
    if not (
        isinstance(licensee, str)
        and isinstance(expires_at, str)
        and isinstance(signature, str)
        and licensee
        and expires_at
        and signature
    ):
        raise InvalidLicence("licensee, expires_at and signature must be non-empty strings")
    try:
        raw_signature = base64.b64decode(signature, validate=True)
    except (binascii.Error, ValueError):
        raise InvalidLicence("signature is not base64") from None
    try:
        key.verify(raw_signature, canonical_bytes(licensee, expires_at))
    except InvalidSignature:
        raise InvalidLicence("signature does not match") from None
    try:
        when = datetime.fromisoformat(expires_at)
    except ValueError:
        raise InvalidLicence("expires_at is not an ISO 8601 time") from None
    if when.tzinfo is None or when.utcoffset() is None:
        raise InvalidLicence("expires_at needs a timezone offset")
    return Licence(licensee, expires_at, when.astimezone(UTC), signature)
