"""F1 Formats: every identifier sent and looked up in every PRD format.
Expected: one case per identifier; identical answers.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from typing import Any

from contract import Client
from generator import Gen, Outcome, Scenario, lookup


def generate(g: Gen) -> Scenario:
    kind = g.rng.choice(["phone", "upi", "url", "sender_id"])
    _, _, normalised = g.identifier(kind)
    spellings = g.spellings(kind, normalised)
    s = g.scenario(f"{kind} in {len(spellings)} spellings")
    for spelled, person in zip(spellings, g.people(len(spellings)), strict=True):
        s.reports.append(
            g.report(person, kind, spelled, occurred=g.ago(hours=g.rng.uniform(2, 72)))
        )

    @s.check("2", "every spelling joins one case")
    def _check_1(c: Client, o: Outcome) -> None:
        cases = {r["case_id"] for r in o.replies if isinstance(r, dict) and "case_id" in r}
        merged = [r.get("merged") for r in o.replies if isinstance(r, dict)]
        if len(cases) != 1 or merged != [False] + [True] * (len(merged) - 1):
            raise AssertionError(f"{len(cases)} cases, merged flags {merged}")

    @s.check("2", "every spelling gets the identical answer")
    def _check_2(c: Client, o: Outcome) -> None:
        answers: list[dict[str, Any]] = [lookup(c, kind, v) for v in spellings]
        if any(a != answers[0] for a in answers[1:]):
            counts = [a["report_count"] for a in answers]
            raise AssertionError(f"answers differ across spellings (report counts {counts})")
        if answers[0]["report_count"] != len(spellings):
            raise AssertionError(f"report_count {answers[0]['report_count']}")

    return s
