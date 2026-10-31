"""Masking: shared/vectors/mask.json for 0, 1, 2 and 3 reporters, all four types.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.mask import display_value

VECTORS = Path(__file__).resolve().parents[2] / "shared" / "vectors" / "mask.json"
CASES: list[dict[str, Any]] = json.loads(VECTORS.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize(
    "case", CASES, ids=[f"{c['type']}:{c['normalised']}:{c['distinct_reporters']}" for c in CASES]
)
def test_vector(case: dict[str, Any]) -> None:
    got = display_value(case["type"], case["normalised"], case["distinct_reporters"])
    assert got == case["expected"]


@settings(max_examples=1000)
@given(st.text("0123456789", min_size=10, max_size=10), st.integers(0, 2))
def test_masked_phone_never_shows_the_middle(digits: str, reporters: int) -> None:
    shown = display_value("phone", f"+91{digits}", reporters)
    assert shown == f"{digits[:2]}XXXXX{digits[-3:]}"


@settings(max_examples=1000)
@given(st.text("abcdefghijklmnopqrstuvwxyz0123456789", min_size=2, max_size=20))
def test_masked_upi_shows_only_first_character(handle: str) -> None:
    shown = display_value("upi", f"{handle}@okaxis", 2)
    assert shown == f"{handle[0]}***@okaxis"
