"""R2 Real sudden wave: 10 to 20 reporters within 3 hours, own words, incident times spread.
Expected: KNOWN_SCAM.

This is the case the coordinated-burst cap must not catch: as sudden as a bombing, but from
unrelated people who were called at different times and write their own words.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from datetime import timedelta

from families._shared import accepted, known_and_unmasked
from generator import Gen, Scenario


def generate(g: Gen) -> Scenario:
    n = g.rng.randint(10, 20)
    kind, _, normalised = g.identifier()
    s = g.scenario(f"{n} people in 3 hours, {kind}")
    end = g.ago(minutes=g.rng.uniform(20, 120))
    spellings = g.spellings(kind, normalised)
    scam_type = g.rng.choice(["digital-arrest", "courier-customs", "otp-call"])
    pincode = g.area()
    for i, person in enumerate(g.people(n)):
        # Calls spread evenly over the 3 hours, so no 15-minute bunch.
        occurred = end - timedelta(hours=3) * ((i + g.rng.random()) / n)
        s.reports.append(
            g.report(
                person,
                kind,
                g.rng.choice(spellings),
                occurred=occurred,
                pincode=pincode if g.rng.random() < 0.6 else None,
                scam_type=scam_type,
                delay_minutes=g.rng.uniform(5, 50),
            )
        )
    accepted(s)
    known_and_unmasked(s, kind, normalised)
    return s
