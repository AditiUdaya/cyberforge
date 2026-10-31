"""shared/data and shared/vectors match PRD Appendix B and C and are internally consistent.

Owner: B. Filled in by: B1.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SHARED = Path(__file__).resolve().parents[2] / "shared"
TYPES = {"phone", "upi", "url", "sender_id"}


def _items(name: str) -> list[dict[str, Any]]:
    doc = json.loads((SHARED / "data" / f"{name}.json").read_text(encoding="utf-8"))
    items: list[dict[str, Any]] = doc["items"]
    return items


def _cases(name: str) -> list[dict[str, Any]]:
    doc = json.loads((SHARED / "vectors" / f"{name}.json").read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = doc["cases"]
    return cases


def test_areas_are_the_25_prd_points() -> None:
    areas = _items("areas")
    prd = [a for a in areas if a["source"] == "prd"]
    assert len(prd) == 25
    assert len({a["pincode"] for a in areas}) == len(areas)
    hsr = next(a for a in areas if a["pincode"] == "560102")
    assert (hsr["locality"], hsr["lat"], hsr["lng"]) == ("HSR Layout", 12.9116, 77.6473)
    for a in areas:
        assert len(a["pincode"]) == 6 and a["pincode"].isdigit()
        assert 6 <= a["lat"] <= 37 and 68 <= a["lng"] <= 98


def test_verified_list_is_appendix_c() -> None:
    verified = _items("verified")
    assert len(verified) == 19
    assert {v["type"] for v in verified} <= TYPES
    counts = {t: sum(v["type"] == t for v in verified) for t in TYPES}
    assert counts == {"phone": 11, "sender_id": 5, "url": 2, "upi": 1}


def test_scam_types_and_channels() -> None:
    assert len(_items("scam_types")) == 13
    assert {"digital-arrest", "job-offer", "other"} <= {s["id"] for s in _items("scam_types")}
    assert [c["id"] for c in _items("channels")] == [
        "Phone call",
        "SMS or WhatsApp",
        "QR code",
        "Fake website",
        "UPI request",
        "Something else",
    ]


def test_short_codes_cover_the_verified_helplines() -> None:
    codes = {c["value"] for c in _items("short_codes")}
    assert {"1930", "1909"} <= codes


def test_normalise_vectors_include_every_prd_example() -> None:
    cases = _cases("normalise")
    assert {c["type"] for c in cases} == TYPES
    inputs = {(c["type"], c["input"]) for c in cases}
    for prd in [
        ("phone", "+91 98765 43210"),
        ("phone", "09876543210"),
        ("phone", "98765-43210"),
        ("phone", "919876543210"),
        ("phone", "12345"),
        ("upi", "Ravi12@OKAXIS"),
        ("url", "http://www.sbi-kyc.in/pay?utm=sms"),
        ("sender_id", "VM-HDFCBK"),
        ("sender_id", "AD-HDFCBK"),
        ("sender_id", "HDFCBK"),
    ]:
        assert prd in inputs
    for v in _items("verified"):
        assert (v["type"], v["value"]) in inputs, v
    assert sum(c["source"] == "ours" for c in cases) >= 60
    assert any(c["expected"] is None for c in cases)


def test_mask_vectors_cover_0_to_3_reporters_for_all_types() -> None:
    cases = _cases("mask")
    for t in TYPES:
        seen = {c["distinct_reporters"] for c in cases if c["type"] == t}
        assert {0, 1, 2, 3} <= seen
    for c in cases:
        if c["distinct_reporters"] >= 3:
            assert c["expected"] == c["normalised"]
        else:
            assert c["expected"] != c["normalised"]
