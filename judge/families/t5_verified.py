"""T5 Verified under attack: bombing the Appendix C values.
Expected: always VERIFIED_BUSINESS.

The attack looks as real as possible (unrelated people, own words, spread over days), so only
the verified list can hold the line.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from contract import Client
from generator import Gen, Outcome, Scenario, lookup, verified


def generate(g: Gen) -> Scenario:
    target = g.rng.choice(verified())
    s = g.scenario(f"{target['type']} {target['owner']}")
    kind, value = str(target["type"]), str(target["value"])
    for person in g.people(g.rng.randint(10, 40)):
        s.reports.append(
            g.report(person, kind, value, occurred=g.ago(hours=g.rng.uniform(1, 24 * 7)))
        )

    @s.check("bonus:verified", "stays VERIFIED_BUSINESS")
    def _check_1(c: Client, o: Outcome) -> None:
        verdict = lookup(c, kind, value)["verdict"]
        if verdict != "VERIFIED_BUSINESS":
            raise AssertionError(f"{value!r} is {verdict}")

    return s
