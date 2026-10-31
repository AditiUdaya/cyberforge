"""Metamorphic transforms change only things that must not matter.

Owner: B. Filled in by: B5.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from families import FAMILIES
from generator import Gen
from metamorphic import FAMILIES_USED, TRANSFORMS, respell, transform

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


def _key(body: dict[str, object]) -> tuple[object, object]:
    return body["reporter_id"], body["report_id"]


def digits(text: str) -> str:
    return "".join(ch for ch in text if ch.isdigit())


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("phone", "+91 98765 43210"),
        ("phone", "1800 1600"),
        ("phone", "1860 419 5555"),
        ("phone", "1930"),
        ("upi", "ravi12@okaxis"),
        ("url", "https://sbi-kyc.in/pay"),
        ("sender_id", "VM-HDFCBK"),
        ("sender_id", "HDFCBK"),
        ("sender_id", "jd-hdfcbk"),
        ("url", "http://www.sbi-kyc.in/pay?utm=sms"),
        ("url", "sbi-kyc.in/pay/"),
    ],
)
def test_respelling_keeps_the_identifier(kind: str, value: str) -> None:
    other = respell(kind, value)
    assert other != value
    if kind == "phone":
        if digits(value).startswith(("1800", "1860")) or len(digits(value)) < 10:
            assert digits(other) == digits(value)
        else:
            assert digits(other)[-10:] == digits(value)[-10:]
    if kind == "upi":
        assert other.lower().strip() == value
    if kind == "sender_id":
        assert other.upper()[-6:] == value.upper()[-6:]
        assert other.upper().count("-") <= 1
    if kind == "url":
        assert "www.www." not in other
        assert "sbi-kyc.in/pay" in other


@pytest.mark.parametrize("family", FAMILIES_USED)
@pytest.mark.parametrize("name", TRANSFORMS)
def test_transforms_keep_every_instant_and_person(family: str, name: str) -> None:
    original = FAMILIES[family](Gen(family, 3, "s", NOW))
    changed = transform(original, name, seed=3)
    valid = [s.body for s in changed if s.expect == frozenset({201})]
    assert len(valid) == len(original.reports)
    by_id = {_key(s.body): s.body for s in original.reports}
    for body in valid:
        before = by_id[_key(body)]
        for field in ("occurred_at", "reported_at"):
            assert datetime.fromisoformat(body[field]) == datetime.fromisoformat(before[field])
        assert body["ip_prefix"] == before["ip_prefix"]
        assert body["note"] == before["note"]
