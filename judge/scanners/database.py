"""Database free of raw identifiers, reporter fields and note text.

Reads the raw bytes of the SQLite file and its WAL after a full simulator run. Claimant name
and email are the one exception the design keeps (for review, never returned or logged); they
are left out of this scan and covered by the reply and log scanners instead.

Owner: B. Filled in by: B7.
"""

from __future__ import annotations

from pathlib import Path

from scanners.responses import Exchange, secrets_sent

MIN_IDENTIFIER = 8


def identifiers_sent(log: list[Exchange]) -> set[str]:
    """Identifier values as sent, plus the bare 10 digits of every phone number."""
    found: set[str] = set()
    for x in log:
        if x.path != "/reports" or not isinstance(x.sent, dict) or x.status != 201:
            continue
        value = str(x.sent.get("identifier_value", "")).strip()
        kind = x.sent.get("identifier_type")
        if kind == "phone":
            digits = "".join(ch for ch in value if ch.isdigit())
            if len(digits) >= 10:
                found.add(digits[-10:])
        elif kind in ("upi", "url") and len(value) >= MIN_IDENTIFIER:
            found.add(value.lower().split("://", 1)[-1].removeprefix("www.").split("?")[0])
    return found


def scan(folder: Path, log: list[Exchange]) -> list[str]:
    files = sorted(folder.glob("scam_map.sqlite*"))
    if not files:
        return [f"no database found in {folder}"]
    data = b"".join(f.read_bytes() for f in files)
    reporter_secrets = {
        s
        for s in secrets_sent(log)
        if not any(
            s == str(x.sent.get(k))
            for x in log
            if isinstance(x.sent, dict)
            for k in ("claimant_name", "contact_email")
        )
    }
    findings = [
        f"database holds a reporter field or note: {s[:30]!r}"
        for s in reporter_secrets
        if s.encode() in data
    ]
    findings += [
        f"database holds a raw identifier: {v[:4]}..."
        for v in identifiers_sent(log)
        if v.encode() in data
    ]
    return findings
