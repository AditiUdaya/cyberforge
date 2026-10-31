"""A2 New type: new type in 24 h; same type seen 29 and 31 days ago.
Expected: NEW_TYPE only when unseen in the 30 days before.

"31 days ago" is placed at 31.5 days, clear of the window edge at 24 h + 30 days.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from contract import Client
from families._shared import area_traffic
from generator import Gen, Outcome, Scenario, alerts

# variant: (age in hours of an earlier report of the new type, or None; NEW_TYPE expected)
VARIANTS: dict[str, tuple[float | None, bool]] = {
    "never seen before": (None, True),
    "seen 29 days ago": (29 * 24.0, False),
    "seen 31 days ago": (31.5 * 24, True),
}


def generate(g: Gen) -> Scenario:
    name = g.rng.choice(sorted(VARIANTS))
    earlier, expected = VARIANTS[name]
    s = g.scenario(name)
    pincode = g.area()
    old_type, new_type = g.rng.sample(["digital-arrest", "job-offer", "sextortion", "otp-call"], 2)
    area_traffic(g, s, pincode, [g.rng.uniform(48, 26 * 24) for _ in range(3)], old_type)
    if earlier is not None:
        area_traffic(g, s, pincode, [earlier], new_type)
    area_traffic(
        g, s, pincode, [g.rng.uniform(1, 20) for _ in range(g.rng.randint(1, 2))], new_type
    )

    @s.check("3", "NEW_TYPE exactly when unseen in the 30 days before")
    def _check_1(c: Client, o: Outcome) -> None:
        found = {a.get("scam_type") for a in alerts(c, pincode) if a["type"] == "NEW_TYPE"}
        want = {new_type} if expected else set()
        if found != want:
            raise AssertionError(f"NEW_TYPE for {sorted(map(str, found))}, want {sorted(want)}")

    @s.check("3", "no SPIKE from one or two reports")
    def _check_2(c: Client, o: Outcome) -> None:
        if any(a["type"] == "SPIKE" for a in alerts(c, pincode)):
            raise AssertionError("SPIKE fired")

    return s
