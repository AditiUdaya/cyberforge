"""Keyed HMACs of identifiers, reporter_id and ip_prefix (connection /24 or /48 when absent).
Keys come from environment secrets; raw values are never stored.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os

HMAC_KEY_ENV = "SCAM_MAP_HMAC_KEY"
MIN_KEY_LENGTH = 16


class Keyring:
    """Turns raw values into keyed digests. Each purpose has its own domain, so the
    same text as an identifier and as a reporter_id gives unrelated digests."""

    def __init__(self, key: str) -> None:
        if len(key) < MIN_KEY_LENGTH:
            raise ValueError(f"{HMAC_KEY_ENV} must be at least {MIN_KEY_LENGTH} characters")
        self._key = key.encode()

    @classmethod
    def from_env(cls) -> Keyring:
        key = os.environ.get(HMAC_KEY_ENV)
        if not key:
            raise RuntimeError(f"{HMAC_KEY_ENV} is not set; see docs/SETUP.md")
        return cls(key)

    def digest(self, purpose: str, value: str) -> str:
        message = f"{purpose}\x00{value}".encode()
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()

    def identifier(self, kind: str, normalised: str) -> str:
        return self.digest(f"id:{kind}", normalised)

    def reporter(self, reporter_id: str) -> str:
        return self.digest("reporter", reporter_id.strip())

    def ip_prefix(self, prefix: str) -> str:
        return self.digest("ip", prefix.strip())

    def note_key(self) -> bytes:
        """A separate key for note fingerprints, so sketches are useless without the secret."""
        return hmac.new(self._key, b"notes", hashlib.sha256).digest()


def connection_prefix(host: str | None) -> str:
    """The /24 of an IPv4 address or the /48 of an IPv6 address; never the full address."""
    if not host:
        return "unknown"
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return "unknown"
    bits = 24 if address.version == 4 else 48
    network = ipaddress.ip_network(f"{address}/{bits}", strict=False)
    return str(network.network_address)
