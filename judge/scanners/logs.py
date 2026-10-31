"""Every log line free of identifiers, reporter fields, notes, emails and query strings.

Reads the local server's whole output from a full simulator run (info level, access log off).

Owner: B. Filled in by: B7.
"""

from __future__ import annotations

import re
from pathlib import Path

from scanners.responses import Exchange, scan_file

PATTERNS = {
    "phone number": re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)"),
    "email or UPI ID": re.compile(r"[\w.\-]+@[\w\-]+"),
    "query string": re.compile(r"\?[\w%]+=|[?&](type|value|pincode)="),
    "request path with query": re.compile(r"\"(GET|POST) /\S*\?"),
}


def scan(path: Path, log: list[Exchange]) -> list[str]:
    findings = scan_file(path, log)
    if not path.exists():
        return [f"{path} was not written"]
    for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for name, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.append(f"server.log line {n} has a {name}")
    return findings
