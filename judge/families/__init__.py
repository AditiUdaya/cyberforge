"""One module per scenario family in docs/SPEC.md 'Judge simulator families'.

Each module has generate(gen) -> Scenario. FAMILIES keeps the SPEC's order.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from collections.abc import Callable

from families import (
    a1_spike,
    a2_new_type,
    a3_fakes_never_alert,
    c1_challenge,
    f1_formats,
    m1_map_window,
    r1_campaign,
    r2_wave,
    r3_small,
    t1_bombing,
    t2_fake_accounts,
    t3_spamming,
    t4_junk,
    t5_verified,
    z1_reset,
)
from generator import Gen, Scenario

FAMILIES: dict[str, Callable[[Gen], Scenario]] = {
    "T1": t1_bombing.generate,
    "T2": t2_fake_accounts.generate,
    "T3": t3_spamming.generate,
    "T4": t4_junk.generate,
    "T5": t5_verified.generate,
    "R1": r1_campaign.generate,
    "R2": r2_wave.generate,
    "R3": r3_small.generate,
    "F1": f1_formats.generate,
    "M1": m1_map_window.generate,
    "A1": a1_spike.generate,
    "A2": a2_new_type.generate,
    "A3": a3_fakes_never_alert.generate,
    "C1": c1_challenge.generate,
    "Z1": z1_reset.generate,
}

# Held-out pass-rate thresholds from docs/SPEC.md (fraction of scenarios that must pass).
THRESHOLDS: dict[str, float] = {family: 1.0 for family in FAMILIES} | {"R1": 0.95, "R2": 0.90}
