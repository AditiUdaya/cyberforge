"""SPIKE and NEW_TYPE rules over counted reports in one area, windows from occurred_at.

PRD Appendix A, route 5:
  SPIKE    reports in the last 24 hours are at least double the daily average of the 7 days
           before, and at least 5.
  NEW_TYPE a scam type reported in the last 24 hours that was not seen in that area in the
           30 days before.
Only counted reports are passed in, so fakes the trust rules ignored never set off an alert.

Owner: B. Filled in by: B6.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

WINDOW = timedelta(hours=24)
BASELINE_DAYS = 7
NEW_TYPE_LOOKBACK = timedelta(days=30)
SPIKE_MIN = 5
SPIKE_FACTOR = 2.0

# How far back alerts need to read.
HISTORY = WINDOW + max(timedelta(days=BASELINE_DAYS), NEW_TYPE_LOOKBACK)


def alerts(
    pincode: str, events: Sequence[tuple[datetime, str]], now: datetime
) -> list[dict[str, Any]]:
    """events: (occurred_at, scam_type) of counted reports in the area."""
    recent_start = now - WINDOW
    baseline_start = recent_start - timedelta(days=BASELINE_DAYS)
    lookback_start = recent_start - NEW_TYPE_LOOKBACK

    recent = [(t, kind) for t, kind in events if recent_start < t <= now]
    baseline = sum(1 for t, _ in events if baseline_start < t <= recent_start)
    per_day = baseline / BASELINE_DAYS

    found: list[dict[str, Any]] = []
    if len(recent) >= SPIKE_MIN and len(recent) >= SPIKE_FACTOR * per_day:
        found.append(
            {
                "type": "SPIKE",
                "pincode": pincode,
                "window": "24h",
                "count": len(recent),
                "baseline_per_day": round(per_day, 2),
            }
        )

    seen_before = {kind for t, kind in events if lookback_start < t <= recent_start}
    for kind in sorted({kind for _, kind in recent} - seen_before):
        found.append({"type": "NEW_TYPE", "pincode": pincode, "scam_type": kind, "window": "24h"})
    return found
