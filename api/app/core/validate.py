"""400 rules: identifier type and value, pincode in the area table,
occurred_at with offset and not in the future.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from functools import cache

from app.core.areas import is_known
from app.shared_data import data_items

# Phones and servers disagree by a few seconds; a report "from the future" within this is accepted.
CLOCK_SKEW = timedelta(minutes=2)

# Times are shown in India Standard Time, as in the PRD examples.
DISPLAY_TZ = timezone(timedelta(hours=5, minutes=30))

OTHER_SCAM_TYPE = "other"
OTHER_CHANNEL = "Something else"


class InvalidReport(ValueError):
    """A report field the API rejects with 400. The message never contains the value."""


def parse_time(raw: str, *, field: str) -> datetime:
    """An ISO 8601 time with an offset, as a UTC datetime."""
    try:
        when = datetime.fromisoformat(raw.strip())
    except ValueError:
        raise InvalidReport(f"invalid {field}: not an ISO 8601 time") from None
    if when.tzinfo is None or when.utcoffset() is None:
        raise InvalidReport(f"invalid {field}: needs a timezone offset")
    return when.astimezone(UTC)


def occurred_at(raw: str, now: datetime) -> datetime:
    when = parse_time(raw, field="occurred_at")
    if when > now + CLOCK_SKEW:
        raise InvalidReport("invalid occurred_at: in the future")
    return when


def pincode(raw: str) -> str:
    value = raw.strip()
    if not is_known(value):
        raise InvalidReport("invalid pincode: not a known area")
    return value


@cache
def _scam_types() -> frozenset[str]:
    return frozenset(str(item["id"]) for item in data_items("scam_types"))


@cache
def _channels() -> frozenset[str]:
    return frozenset(str(item["id"]) for item in data_items("channels"))


def scam_type(raw: str) -> str:
    """Appendix C names as sent; anything else is accepted and stored as other."""
    value = raw.strip()
    return value if value in _scam_types() else OTHER_SCAM_TYPE


def channel(raw: str) -> str:
    value = raw.strip()
    return value if value in _channels() else OTHER_CHANNEL


def to_utc_text(when: datetime) -> str:
    return when.astimezone(UTC).isoformat()


def to_display(utc_text: str) -> str:
    return datetime.fromisoformat(utc_text).astimezone(DISPLAY_TZ).isoformat()
