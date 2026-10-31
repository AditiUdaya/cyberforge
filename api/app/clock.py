"""Injectable clock: the single source of 'now' for windows, rate limits and licence expiry.
Tests swap it to travel in time.

Owner: B. Filled in by: B0.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Current time, timezone-aware, in UTC."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """A clock that only moves when a test moves it."""

    def __init__(self, start: datetime) -> None:
        self._now = _to_utc(start)

    def now(self) -> datetime:
        return self._now

    def set(self, when: datetime) -> None:
        self._now = _to_utc(when)

    def advance(self, delta: timedelta) -> None:
        self._now += delta


def _to_utc(when: datetime) -> datetime:
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("clock times must carry a timezone")
    return when.astimezone(UTC)
