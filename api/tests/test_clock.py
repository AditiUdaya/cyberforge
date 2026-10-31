"""Injectable clock: real clock is UTC-aware; the fixed clock moves only when told to.

Owner: B. Filled in by: B0.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.clock import FixedClock, SystemClock


def test_system_clock_is_utc_aware() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_fixed_clock_stays_put() -> None:
    start = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
    clock = FixedClock(start)
    assert clock.now() == start
    assert clock.now() == start


def test_fixed_clock_advances_and_sets() -> None:
    start = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
    clock = FixedClock(start)
    clock.advance(timedelta(minutes=5))
    assert clock.now() == start + timedelta(minutes=5)
    clock.set(start - timedelta(days=365))
    assert clock.now() == start - timedelta(days=365)


def test_fixed_clock_normalises_offsets_to_utc() -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    clock = FixedClock(datetime(2026, 10, 31, 17, 30, tzinfo=ist))
    assert clock.now() == datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
    assert clock.now().utcoffset() == timedelta(0)


def test_fixed_clock_rejects_naive_times() -> None:
    with pytest.raises(ValueError, match="timezone"):
        FixedClock(datetime(2026, 10, 31, 12, 0))
