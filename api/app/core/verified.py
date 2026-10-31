"""The PRD Appendix C verified values from shared/data/verified.json, normalised once.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

from functools import cache

from app.core.normalise import IdentifierType, normalise
from app.shared_data import data_items


@cache
def verified_values() -> frozenset[tuple[str, str]]:
    pairs = set()
    for item in data_items("verified"):
        kind: IdentifierType = item["type"]
        pairs.add((kind, normalise(kind, str(item["value"]))))
    return frozenset(pairs)


def is_verified(kind: IdentifierType, normalised: str) -> bool:
    return (kind, normalised) in verified_values()
