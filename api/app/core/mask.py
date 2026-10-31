"""display_value masking until 3 distinct reporters: 98XXXXX210, r***@okaxis, sbi***.in/..., HD****.
Cases in shared/vectors/mask.json.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

from app.core.normalise import IdentifierType
from app.core.trust_config import UNMASK_MIN_REPORTERS


def display_value(kind: IdentifierType, normalised: str, distinct_reporters: int) -> str:
    """What the app may show: the full value only once enough different people reported it."""
    if distinct_reporters >= UNMASK_MIN_REPORTERS:
        return normalised
    if kind == "phone":
        return _phone(normalised)
    if kind == "upi":
        handle, _, psp = normalised.partition("@")
        return f"{handle[:1]}***@{psp}"
    if kind == "url":
        host = normalised.removeprefix("https://").split("/", 1)[0]
        labels = host.split(".")
        return f"{labels[0][:3]}***.{labels[-1]}/..."
    return f"{normalised[:2]}****"


def _phone(normalised: str) -> str:
    digits = normalised.removeprefix("+91") if normalised.startswith("+91") else normalised
    if len(digits) >= 8:
        return f"{digits[:2]}{'X' * (len(digits) - 5)}{digits[-3:]}"
    return f"{digits[:2]}{'X' * (len(digits) - 2)}"
