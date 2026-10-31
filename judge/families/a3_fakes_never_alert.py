"""A3 Fakes never alert: T1 to T3 aimed at a quiet area.
Expected: no alerts.

The quiet area has one counted report a day for a week. The attack uses the same scam type,
so only the fakes' volume could set off an alert.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from datetime import timedelta

from families._shared import area_traffic, no_alerts, steady_days
from generator import Gen, Person, Scenario


def generate(g: Gen) -> Scenario:
    attack = g.rng.choice(["T1 bombing", "T2 fake accounts", "T3 spamming"])
    s = g.scenario(attack)
    pincode = g.area()
    scam_type = g.rng.choice(["fake-kyc-link", "lottery-prize", "courier-customs"])
    area_traffic(g, s, pincode, steady_days(g, 1), scam_type)

    kind, value, _ = g.identifier()
    start = g.ago(hours=g.rng.uniform(2, 18))
    if attack == "T1 bombing":
        wifi, script = g.prefix(), g.note()
        senders = [g.person(wifi) for _ in range(40)]
        notes = [script] * 40
    elif attack == "T2 fake accounts":
        wifi = g.prefix()
        senders = g.people(22, prefix=wifi)
        notes = [g.note() for _ in senders]
    else:
        one = g.person()
        senders = [Person(one.reporter_id, one.ip_prefix)] * 6
        notes = [g.note()] * 6
    for i, (person, note) in enumerate(zip(senders, notes, strict=True)):
        s.reports.append(
            g.report(
                person,
                kind,
                value,
                occurred=start + timedelta(minutes=g.rng.uniform(0, 12)),
                pincode=pincode,
                note=note,
                scam_type=scam_type,
                delay_minutes=15 + i * 1.2,
                expect=frozenset({201, 429}),
            )
        )

    no_alerts(s, "bonus:fakes", pincode)
    return s
