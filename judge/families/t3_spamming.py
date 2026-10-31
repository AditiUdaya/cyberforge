"""T3 Spamming: one reporter 6 times in an hour, with prefix and note variants.
Expected: distinct_reporters 1; 429 after 3 allowed.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from contract import Client
from families._shared import never_known_scam, one_reporter
from generator import Gen, Outcome, Person, Scenario

ALLOWED = 3
TIMES = 6


def generate(g: Gen) -> Scenario:
    variant = g.rng.choice(["same prefix", "other prefixes", "other notes"])
    s = g.scenario(variant)
    kind, value, normalised = g.identifier()
    spammer = g.person()
    script = g.note()
    start = g.ago(hours=g.rng.uniform(1.2, 10))
    for i in range(TIMES):
        person = spammer
        if variant == "other prefixes":
            person = Person(spammer.reporter_id, g.prefix())
        s.reports.append(
            g.report(
                person,
                kind,
                value,
                occurred=start,
                note=g.note() if variant == "other notes" else script,
                delay_minutes=10 * i + g.rng.uniform(0, 9),
                expect=frozenset({201}) if i < ALLOWED else frozenset({429}),
            )
        )

    @s.check("1", "429 after 3 reports in an hour")
    def _check_1(c: Client, o: Outcome) -> None:
        want = [201] * ALLOWED + [429] * (TIMES - ALLOWED)
        if o.statuses != want:
            raise AssertionError(f"statuses {o.statuses}, want {want}")

    one_reporter(s, kind, normalised)
    never_known_scam(s, "1", kind, normalised)
    return s
