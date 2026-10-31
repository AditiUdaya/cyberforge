"""Replies never contain reporter_id, ip_prefix, notes or non-area coordinates; unmasked only at 3+.

Also records every exchange, so the other scanners know exactly what was sent.

Owner: B. Filled in by: B7.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from contract import REPO

MIN_SECRET = 6


@dataclass(frozen=True)
class Exchange:
    method: str
    path: str
    sent: Any
    status: int
    text: str


@dataclass
class Recorder:
    """Wraps an httpx client and keeps every request and reply."""

    inner: Any
    log: list[Exchange] = field(default_factory=list)

    def get(self, url: str, *, params: Mapping[str, str] | None = None) -> Any:
        response = self.inner.get(url, params=params)
        self.log.append(
            Exchange("GET", url, dict(params or {}), response.status_code, response.text)
        )
        return response

    def post(
        self,
        url: str,
        *,
        json: Any = None,
        content: bytes | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        response = self.inner.post(url, json=json, content=content, headers=headers)
        self.log.append(Exchange("POST", url, json, response.status_code, response.text))
        return response


def secrets_sent(log: list[Exchange]) -> set[str]:
    """Reporter fields, notes and claimant contact: things no reply or log may ever show."""
    found: set[str] = set()
    for x in log:
        if not isinstance(x.sent, dict):
            continue
        for key in ("reporter_id", "ip_prefix", "note", "claimant_name", "contact_email"):
            value = x.sent.get(key)
            if isinstance(value, str) and len(value.strip()) >= MIN_SECRET:
                found.add(value.strip())
    return found


@cache
def area_points() -> dict[str, tuple[float, float]]:
    doc = json.loads((REPO / "shared" / "data" / "areas.json").read_text(encoding="utf-8"))
    return {str(a["pincode"]): (float(a["lat"]), float(a["lng"])) for a in doc["items"]}


def scan(log: list[Exchange]) -> list[str]:
    findings: list[str] = []
    secrets = secrets_sent(log)
    for x in log:
        for secret in secrets:
            if secret in x.text:
                findings.append(
                    f"{x.method} {x.path} reply contains a sent secret: {secret[:30]!r}"
                )
                break
        try:
            body = json.loads(x.text)
        except ValueError:
            findings.append(f"{x.method} {x.path} reply is not JSON")
            continue
        if x.path == "/lookup" and x.status == 200:
            findings += _lookup(body)
        if x.path == "/map" and x.status == 200:
            findings += _map(body)
    return findings


def _lookup(body: dict[str, Any]) -> list[str]:
    out = []
    if body["verdict"] != "VERIFIED_BUSINESS" and body["distinct_reporters"] < 3:
        shown = str(body["display_value"])
        if "XX" not in shown and "**" not in shown:
            out.append(
                f"unmasked value with {body['distinct_reporters']} reporters: {shown[:4]}..."
            )
    for item in body.get("evidence", []):
        if set(item) != {"occurred_at", "channel", "scam_type", "pincode"}:
            out.append(f"evidence has extra fields: {sorted(set(item))}")
    return out


def _map(body: dict[str, Any]) -> list[str]:
    out = []
    for cluster in body["clusters"]:
        point = area_points().get(str(cluster["pincode"]))
        if point is None or (cluster["lat"], cluster["lng"]) != point:
            out.append(f"map point for {cluster['pincode']} is not its Appendix B point")
    return out


def scan_file(path: Path, log: list[Exchange]) -> list[str]:
    """Shared by the log and database scanners: no sent secret anywhere in a file's bytes."""
    if not path.exists():
        return []
    data = path.read_bytes()
    return [
        f"{path.name} contains a sent secret: {secret[:30]!r}"
        for secret in secrets_sent(log)
        if secret.encode() in data
    ]
