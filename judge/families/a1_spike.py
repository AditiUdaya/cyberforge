"""A1 Spike: steady 2 a day then 10 in 24 h; steady areas; exactly double; double with only 4.
Expected: alerts exactly where the PRD rule says.

PRD rule: SPIKE when reports in the last 24 hours are at least double the daily average of the
7 days before, and at least 5. All reports here are counted (different people, identifiers and
words), and share one scam type so NEW_TYPE stays quiet.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from contract import Client
from families._shared import area_traffic, last_day, no_alerts, steady_days
from generator import Gen, Outcome, Scenario, alerts, areas

# variant: (per day for the 7 days before, count in the last 24 hours, SPIKE expected)
VARIANTS = {
    "spike 2/day then 10": (2, 10, True),
    "steady 2/day": (2, 2, False),
    "exactly double, 3/day then 6": (3, 6, True),
    "double but only 4": (2, 4, False),
}


def generate(g: Gen) -> Scenario:
    name = g.rng.choice(sorted(VARIANTS))
    per_day, today, spike = VARIANTS[name]
    s = g.scenario(name)
    bengaluru = sorted(p for p, a in areas().items() if a["city"] == "Bengaluru")
    pincode, quiet = g.rng.sample(bengaluru, 2)
    scam_type = g.rng.choice(["fake-kyc-link", "otp-call", "job-offer"])
    area_traffic(g, s, pincode, steady_days(g, per_day) + last_day(g, today), scam_type)
    area_traffic(g, s, quiet, steady_days(g, 2) + last_day(g, 2), scam_type)

    @s.check("3", "SPIKE exactly when the PRD rule says")
    def _check_1(c: Client, o: Outcome) -> None:
        found = [a for a in alerts(c, pincode) if a["type"] == "SPIKE"]
        if not spike:
            if found:
                raise AssertionError(f"SPIKE fired for {per_day}/day then {today}")
            return
        if len(found) != 1:
            raise AssertionError(f"no SPIKE for {per_day}/day then {today}")
        a = found[0]
        if a["count"] != today or abs(a["baseline_per_day"] - per_day) > 0.01:
            raise AssertionError(f"SPIKE count {a['count']} baseline {a['baseline_per_day']}")

    no_alerts(s, "3", quiet)
    return s
