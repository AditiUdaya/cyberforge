"""T2 Fake accounts: 22 reporter ids on one prefix within 2 hours.
Expected: distinct_reporters 1; never KNOWN_SCAM.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from families._shared import never_known_scam, one_reporter
from generator import Gen, Scenario

ACCOUNTS = 22


def generate(g: Gen) -> Scenario:
    notes = g.rng.choice(["varied", "empty", "copied"])
    s = g.scenario(f"one prefix, {notes} notes")
    kind, value, normalised = g.identifier()
    wifi = g.prefix()
    script = g.note()
    start = g.ago(hours=g.rng.uniform(2.5, 30))
    for account in g.people(ACCOUNTS, prefix=wifi):
        text = {"varied": g.note(), "empty": "", "copied": script}[notes]
        s.reports.append(
            g.report(
                account,
                kind,
                value,
                occurred=start,
                note=text,
                delay_minutes=g.rng.uniform(5, 120),
            )
        )

    one_reporter(s, kind, normalised)
    never_known_scam(s, "1", kind, normalised)
    return s
