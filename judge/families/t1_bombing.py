"""T1 Report-bombing: 40 reporters on a real business number within an hour,
with prefix and note variants.
Expected: never KNOWN_SCAM; no alert.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from datetime import timedelta

from families._shared import never_known_scam, no_alerts
from generator import Gen, Scenario

FRIENDS = 40


def generate(g: Gen) -> Scenario:
    prefixes = g.rng.choice([1, 10, 40])
    notes = g.rng.choice(["copied", "empty", "edited"])
    s = g.scenario(f"{prefixes} prefixes, {notes} notes")

    business = g.landline()
    value = f"+91 {business[:2]} {business[2:6]} {business[6:]}"
    pincode = g.area()
    pool = [g.prefix() for _ in range(prefixes)]
    script = g.note()
    scam_type = g.rng.choice(["fake-customer-care", "upi-refund-qr", "lottery-prize"])
    # The rival tells everyone the same story, so the incident times bunch together.
    incident = g.ago(hours=g.rng.uniform(1.5, 20))
    for i in range(FRIENDS):
        text = {"copied": script, "empty": "", "edited": _edit(g, script)}[notes]
        occurred = incident + timedelta(minutes=g.rng.uniform(0, 15))
        s.reports.append(
            g.report(
                g.person(pool[i % prefixes]),
                "phone",
                value,
                occurred=occurred,
                pincode=pincode,
                note=text,
                scam_type=scam_type,
                delay_minutes=g.rng.uniform(15, 60),
            )
        )

    never_known_scam(s, "1", "phone", value)
    no_alerts(s, "bonus:fakes", pincode)
    return s


def _edit(g: Gen, text: str) -> str:
    """A light edit: one word swapped, or a few characters added."""
    words = text.split()
    i = g.rng.randrange(len(words))
    words[i] = g.rng.choice(["really", "totally", "very", "fully", words[i].upper()])
    return " ".join(words) + g.rng.choice(["", "!", " pls share", " beware"])
