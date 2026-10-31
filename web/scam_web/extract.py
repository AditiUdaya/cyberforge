"""Finds phone numbers, UPI IDs, links and SMS sender IDs in a pasted message.

Returns each identifier once, in order of first appearance, in standard form. Links and UPI IDs
are taken out of the text before looking for numbers, so their digits are not read as phones.
Cases in shared/vectors/extract.json.

Owner: A. Filled in by: A1.
"""

from __future__ import annotations

import re

from scam_web.normalise import IdentifierType, InvalidIdentifier, normalise

_URL = re.compile(
    r"(?:https?://|www\.)[^\s<>\"']+"
    r"|\b[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:in|com|net|org|co|info|online|xyz|app|link)"
    r"(?:/[^\s<>\"']*)?",
    re.IGNORECASE,
)
_UPI = re.compile(r"\b[\w.\-]{2,256}@[A-Za-z][A-Za-z0-9]{1,63}\b(?!\.)")
_SENDER = re.compile(r"\b[A-Za-z]{2}-[A-Za-z]{6}(?:-[A-Za-z])?\b")
_PHONE = re.compile(r"(?:\(?\+?\d[\d\s().-]{1,18}\d)")
_TRAILING = ".,;:!?)]}'\""


def extract(text: str) -> list[tuple[IdentifierType, str]]:
    found: list[tuple[int, IdentifierType, str]] = []
    remaining = text

    def take(pattern: re.Pattern[str], kind: IdentifierType) -> None:
        nonlocal remaining
        for match in pattern.finditer(remaining):
            raw = match.group(0).rstrip(_TRAILING)
            try:
                found.append((match.start(), kind, normalise(kind, raw)))
            except InvalidIdentifier:
                continue
            start, end = match.span()
            remaining = remaining[:start] + " " * (end - start) + remaining[end:]

    take(_UPI, "upi")
    take(_URL, "url")
    take(_SENDER, "sender_id")
    take(_PHONE, "phone")

    seen: set[tuple[str, str]] = set()
    ordered: list[tuple[IdentifierType, str]] = []
    for _, kind, value in sorted(found, key=lambda f: f[0]):
        if (kind, value) not in seen:
            seen.add((kind, value))
            ordered.append((kind, value))
    return ordered


def detect(value: str) -> tuple[IdentifierType, str] | None:
    """The type and standard form of a single typed value, or None if it is not one."""
    text = value.strip()
    order: list[IdentifierType] = ["upi", "sender_id", "phone", "url"]
    for kind in order:
        try:
            return kind, normalise(kind, text)
        except InvalidIdentifier:
            continue
    return None
