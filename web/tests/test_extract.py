"""The web normaliser and extractor pass the shared vectors, like the API does.

Owner: A. Filled in by: A1.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from scam_web.extract import detect, extract
from scam_web.normalise import InvalidIdentifier, normalise
from scam_web.settings import shared_dir


def cases(name: str) -> list[dict[str, Any]]:
    path = shared_dir() / "vectors" / f"{name}.json"
    found: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))["cases"]
    return found


@pytest.mark.parametrize("case", cases("normalise"), ids=lambda c: f"{c['type']}:{c['input']!r}")
def test_normalise_vector(case: dict[str, Any]) -> None:
    if case["expected"] is None:
        with pytest.raises(InvalidIdentifier):
            normalise(case["type"], case["input"])
    else:
        assert normalise(case["type"], case["input"]) == case["expected"]


@pytest.mark.parametrize("case", cases("extract"), ids=lambda c: c["text"][:40])
def test_extract_vector(case: dict[str, Any]) -> None:
    want = [(e["type"], e["value"]) for e in case["expected"]]
    assert extract(case["text"]) == want


@pytest.mark.parametrize(
    ("value", "want"),
    [
        ("+91 98765 43210", ("phone", "+919876543210")),
        ("Ravi12@OKAXIS", ("upi", "ravi12@okaxis")),
        ("http://www.sbi-kyc.in/pay?utm=sms", ("url", "https://sbi-kyc.in/pay")),
        ("VM-HDFCBK", ("sender_id", "HDFCBK")),
        ("1930", ("phone", "1930")),
        ("12345", None),
        ("test", None),
    ],
)
def test_detect_single_values(value: str, want: tuple[str, str] | None) -> None:
    assert detect(value) == want
