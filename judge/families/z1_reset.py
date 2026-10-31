"""Z1 Reset: reset after any family.
Expected: every lookup NO_REPORTS, map and alerts empty, licence intact.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from datetime import timedelta

from contract import Client
from families._shared import area_traffic, last_day, real_reports, steady_days
from generator import Gen, Outcome, Scenario, alerts, area_map, lookup


def generate(g: Gen) -> Scenario:
    s = g.scenario("campaign and spike, then reset")
    kind, _, normalised = g.identifier()
    pincode = g.area()
    real_reports(g, s, kind, normalised, 6, span=timedelta(days=3), pincodes=[pincode])
    area_traffic(g, s, pincode, steady_days(g, 1) + last_day(g, 8), "job-offer")
    s.reset_before_checks = True

    @s.check("2", "every lookup is NO_REPORTS after reset")
    def _check_1(c: Client, o: Outcome) -> None:
        body = lookup(c, kind, normalised)
        if body["verdict"] != "NO_REPORTS" or body["report_count"] != 0:
            raise AssertionError(f"{body['verdict']} with {body['report_count']} reports")

    @s.check("3", "map and alerts are empty after reset")
    def _check_2(c: Client, o: Outcome) -> None:
        if area_map(c, pincode, days=30, radius_km=50) or alerts(c, pincode):
            raise AssertionError("map or alerts still show data")

    @s.check("5", "licence intact after reset")
    def _check_3(c: Client, o: Outcome) -> None:
        body = c.get("/license").json()
        if body.get("valid") is not True:
            raise AssertionError(f"licence after reset: {body}")

    return s
