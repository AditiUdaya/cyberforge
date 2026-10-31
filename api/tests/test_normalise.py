"""Normaliser: every shared/vectors/normalise.json case plus Hypothesis properties and junk -> 400.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.normalise import IdentifierType, InvalidIdentifier, normalise

VECTORS = Path(__file__).resolve().parents[2] / "shared" / "vectors" / "normalise.json"
CASES: list[dict[str, Any]] = json.loads(VECTORS.read_text(encoding="utf-8"))["cases"]
TYPES: list[IdentifierType] = ["phone", "upi", "url", "sender_id"]
EXAMPLES = 1000


@pytest.mark.parametrize("case", CASES, ids=[f"{c['type']}:{c['input']!r}" for c in CASES])
def test_vector(case: dict[str, Any]) -> None:
    if case["expected"] is None:
        with pytest.raises(InvalidIdentifier):
            normalise(case["type"], case["input"])
    else:
        assert normalise(case["type"], case["input"]) == case["expected"]


@pytest.mark.parametrize("case", [c for c in CASES if c["expected"] is not None])
def test_normal_form_is_a_fixed_point(case: dict[str, Any]) -> None:
    once = normalise(case["type"], case["input"])
    assert normalise(case["type"], once) == once


mobiles = st.tuples(st.sampled_from("6789"), st.text("0123456789", min_size=9, max_size=9)).map(
    "".join
)


def _format(digits: str, style: int) -> str:
    a, b = digits[:5], digits[5:]
    return [
        f"+91 {a} {b}",
        f"0{digits}",
        f"{a}-{b}",
        f"91{digits}",
        digits,
        f"+91-{a}-{b}",
        f"(+91) {a} {b}",
        f"0091 {a} {b}",
        f"  {a} {b}  ",
        f"{a}.{b}",
    ][style]


@settings(max_examples=EXAMPLES)
@given(mobiles, st.integers(0, 9))
def test_every_mobile_format_gives_one_form(digits: str, style: int) -> None:
    assert normalise("phone", _format(digits, style)) == f"+91{digits}"


handles = st.text("abcdefghijklmnopqrstuvwxyz0123456789._-", min_size=2, max_size=30)
psps = st.text("abcdefghijklmnopqrstuvwxyz", min_size=2, max_size=12)


@settings(max_examples=EXAMPLES)
@given(handles, psps, st.booleans())
def test_upi_case_and_spaces_do_not_matter(handle: str, psp: str, shout: bool) -> None:
    raw = f" {handle}@{psp} "
    raw = raw.upper() if shout else raw
    assert normalise("upi", raw) == f"{handle}@{psp}"


labels = st.text("abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=12)
tlds = st.sampled_from(["in", "com", "org", "co.in", "gov.in", "xyz"])
paths = st.lists(st.text("abcdefghijklmnopqrstuvwxyzABC0123456789-_", min_size=1, max_size=8))


@settings(max_examples=EXAMPLES)
@given(labels, tlds, paths, st.sampled_from(["http://", "https://", "", "HTTP://WWW."]))
def test_url_scheme_www_query_and_slash_do_not_matter(
    label: str, tld: str, path: list[str], prefix: str
) -> None:
    tail = "".join(f"/{p}" for p in path)
    raw = f"{prefix}{label}.{tld}{tail}/?utm=sms#x"
    assert normalise("url", raw) == f"https://{label}.{tld}{tail}"


codes = st.text("ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=6, max_size=6)
operators = st.text("ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=2, max_size=2)


@settings(max_examples=EXAMPLES)
@given(codes, operators, st.booleans())
def test_sender_prefix_does_not_matter(code: str, operator: str, lower: bool) -> None:
    raw = f"{operator}-{code}"
    assert normalise("sender_id", raw.lower() if lower else raw) == code


@settings(max_examples=EXAMPLES)
@given(st.sampled_from(TYPES), st.text(max_size=60))
def test_junk_never_crashes(kind: IdentifierType, raw: str) -> None:
    try:
        result = normalise(kind, raw)
    except InvalidIdentifier:
        return
    assert result
    assert normalise(kind, result) == result


@settings(max_examples=EXAMPLES)
@given(st.text("0123456789", max_size=9))
def test_short_digit_strings_are_rejected_unless_allowlisted(raw: str) -> None:
    allowlisted = {"1930", "1909", "112", "100", "101", "102", "108", "1098", "181"}
    if raw in allowlisted or raw.startswith(("1800", "1860")):
        return
    with pytest.raises(InvalidIdentifier):
        normalise("phone", raw)
