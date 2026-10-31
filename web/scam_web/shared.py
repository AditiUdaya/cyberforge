"""Reads shared/data: scam types, channels and short codes, never retyped here.

Owner: A. Filled in by: A0.
"""

from __future__ import annotations

import json
from functools import cache
from typing import Any

from scam_web.settings import shared_dir


@cache
def items(name: str) -> tuple[dict[str, Any], ...]:
    doc = json.loads((shared_dir() / "data" / f"{name}.json").read_text(encoding="utf-8"))
    return tuple(doc["items"])


def scam_type_ids() -> list[str]:
    return [str(s["id"]) for s in items("scam_types")]


def channel_ids() -> list[str]:
    return [str(c["id"]) for c in items("channels")]


def short_codes() -> frozenset[str]:
    return frozenset(str(c["value"]) for c in items("short_codes"))
