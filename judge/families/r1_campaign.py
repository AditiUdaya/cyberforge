"""R1 Real campaign: 5 to 60 unrelated reporters, own words, over 1 to 14 days and several areas.
Expected: KNOWN_SCAM; unmasked once 3 or more.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from datetime import timedelta

from families._shared import accepted, known_and_unmasked, real_reports
from generator import Gen, Scenario


def generate(g: Gen) -> Scenario:
    n = g.rng.randint(5, 60)
    days = g.rng.uniform(1, 14)
    kind, _, normalised = g.identifier()
    s = g.scenario(f"{n} people over {days:.1f} days, {kind}")
    pincodes = [g.area() for _ in range(g.rng.randint(2, 5))]
    real_reports(g, s, kind, normalised, n, span=timedelta(days=days), pincodes=pincodes)
    accepted(s)
    known_and_unmasked(s, kind, normalised)
    return s
