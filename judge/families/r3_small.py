"""R3 Small real: 1 or 2 reporters.
Expected: SUSPICIOUS, masked.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from datetime import timedelta

from contract import Client
from families._shared import accepted, real_reports
from generator import Gen, Outcome, Scenario, lookup, masked_like


def generate(g: Gen) -> Scenario:
    n = g.rng.randint(1, 2)
    kind, _, normalised = g.identifier()
    s = g.scenario(f"{n} people, {kind}")
    real_reports(g, s, kind, normalised, n, span=timedelta(days=g.rng.uniform(0.5, 10)))
    accepted(s)

    @s.check("2", "SUSPICIOUS")
    def _check_1(c: Client, o: Outcome) -> None:
        verdict = lookup(c, kind, normalised)["verdict"]
        if verdict != "SUSPICIOUS":
            raise AssertionError(f"{verdict}, want SUSPICIOUS")

    @s.check("4", "masked under 3 reporters")
    def _check_2(c: Client, o: Outcome) -> None:
        shown = lookup(c, kind, normalised)["display_value"]
        if shown != masked_like(kind, normalised):
            raise AssertionError(f"display_value {shown!r} is not masked")

    return s
