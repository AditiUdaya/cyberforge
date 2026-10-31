"""C1 Challenge: challenge on a number with a real campaign.
Expected: challenged true, never KNOWN_SCAM.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from datetime import timedelta

from contract import Client
from families._shared import real_reports
from generator import Gen, Outcome, Scenario, lookup


def generate(g: Gen) -> Scenario:
    s = g.scenario("business disputes a reported number")
    business = g.landline()
    normalised = f"+91{business}"
    real_reports(g, s, "phone", normalised, g.rng.randint(5, 12), span=timedelta(days=5))
    s.challenges.append(
        {
            "identifier_type": "phone",
            "identifier_value": f"+91 {business[:2]} {business[2:6]} {business[6:]}",
            "claimant_name": g.rng.choice(["Fresh Bakes", "City Pharmacy", "Lakshmi Stores"]),
            "contact_email": f"owner{g.rng.randint(1, 999)}@example.com",
            "proof_note": "GST certificate and shop licence attached.",
        }
    )

    @s.check("bonus:dispute", "challenge accepted as under_review")
    def _check_1(c: Client, o: Outcome) -> None:
        if o.challenge_statuses != [201]:
            raise AssertionError(f"challenge status {o.challenge_statuses}, want [201]")

    @s.check("bonus:dispute", "challenged true and never KNOWN_SCAM")
    def _check_2(c: Client, o: Outcome) -> None:
        body = lookup(c, "phone", normalised)
        if body["challenged"] is not True or body["verdict"] == "KNOWN_SCAM":
            raise AssertionError(f"challenged {body['challenged']}, verdict {body['verdict']}")

    return s
