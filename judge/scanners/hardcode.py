"""No literal phone number, UPI ID, link or sender ID in api/app; they live only in shared/data.

The PRD checks for code like `if number == "+919876543210"`. This reads every string literal
in api/app and fails on anything shaped like an identifier, and on any value from the
verified list or the short-code allowlist.

Owner: B. Filled in by: B7.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from contract import REPO

SHAPES = {
    "phone number": re.compile(r"(?<!\d)(\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"),
    "toll-free number": re.compile(r"(?<!\d)18[06]0[\s-]?\d{3,4}[\s-]?\d{0,4}(?!\d)"),
    "UPI ID": re.compile(r"\b[\w.\-]{2,}@(ok\w+|ybl|paytm|ibl|axl|upi)\b", re.IGNORECASE),
    "link": re.compile(r"https?://[a-z0-9-]+\.[a-z]", re.IGNORECASE),
    "sender ID": re.compile(r"\b[A-Z]{2}-[A-Z]{6}\b"),
}


def _listed_values() -> set[str]:
    """Every identifier the PRD gives us, which must never be compared against in code."""
    values: set[str] = set()
    for name in ("verified", "short_codes"):
        doc = json.loads((REPO / "shared" / "data" / f"{name}.json").read_text(encoding="utf-8"))
        for item in doc["items"]:
            raw = str(item["value"])
            values.add(raw)
            values.add("".join(raw.split()))
    return values


def _literals(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        (n.lineno, n.value)
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]


def scan(root: Path | None = None) -> list[str]:
    root = root or REPO / "api" / "app"
    listed = _listed_values()
    findings = []
    for path in sorted(root.rglob("*.py")):
        where = path.relative_to(REPO) if path.is_relative_to(REPO) else path
        for line, text in _literals(path):
            for name, pattern in SHAPES.items():
                if pattern.search(text):
                    findings.append(f"{where}:{line} has a {name} literal")
            if text.strip() in listed:
                findings.append(f"{where}:{line} hardcodes listed value {text.strip()!r}")
    return findings
