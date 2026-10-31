"""Building blocks the families share: real campaigns, steady area traffic, common checks.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from contract import Client
from generator import Gen, Outcome, Scenario, alerts, lookup, masked_like


def real_reports(
    g: Gen,
    s: Scenario,
    kind: str,
    normalised: str,
    n: int,
    *,
    span: timedelta,
    end: datetime | None = None,
    pincodes: list[str] | None = None,
    scam_type: str | None = None,
) -> None:
    """n unrelated people, each on their own connection, in their own words, at their own time."""
    end = end or g.ago(hours=1)
    kind_type = scam_type or g.rng.choice(["digital-arrest", "fake-kyc-link", "job-offer"])
    spellings = g.spellings(kind, normalised)
    for person in g.people(n):
        occurred = end - span * g.rng.random()
        s.reports.append(
            g.report(
                person,
                kind,
                g.rng.choice(spellings),
                occurred=occurred,
                pincode=g.rng.choice(pincodes) if pincodes else None,
                scam_type=kind_type,
            )
        )


def area_traffic(
    g: Gen, s: Scenario, pincode: str, ages_hours: list[float], scam_type: str
) -> None:
    """Counted reports in one area: each a different person about a different identifier."""
    for age in ages_hours:
        kind, value, _ = g.identifier()
        s.reports.append(
            g.report(
                g.person(),
                kind,
                value,
                occurred=g.ago(hours=age),
                pincode=pincode,
                scam_type=scam_type,
                delay_minutes=g.rng.uniform(2, min(30.0, age * 60 * 0.5)),
            )
        )


def steady_days(g: Gen, per_day: int, days: int = 7) -> list[float]:
    """Ages in hours for per_day reports on each of the `days` days before the last 24 hours."""
    return [24 + 24 * d + g.rng.uniform(1, 23) for d in range(days) for _ in range(per_day)]


def last_day(g: Gen, n: int) -> list[float]:
    return [g.rng.uniform(0.5, 23) for _ in range(n)]


def never_known_scam(s: Scenario, row: str, kind: str, value: str) -> None:
    @s.check(row, "never KNOWN_SCAM")
    def _check_1(c: Client, o: Outcome) -> None:
        verdict = lookup(c, kind, value)["verdict"]
        if verdict == "KNOWN_SCAM":
            raise AssertionError(f"{kind} became KNOWN_SCAM")


def one_reporter(s: Scenario, kind: str, value: str) -> None:
    @s.check("1", "distinct_reporters is 1")
    def _check_2(c: Client, o: Outcome) -> None:
        n = lookup(c, kind, value)["distinct_reporters"]
        if n != 1:
            raise AssertionError(f"distinct_reporters {n}, want 1")


def no_alerts(s: Scenario, row: str, pincode: str) -> None:
    @s.check(row, "no alerts in the area")
    def _check_3(c: Client, o: Outcome) -> None:
        found = alerts(c, pincode)
        if found:
            raise AssertionError(f"unexpected alerts: {[a['type'] for a in found]}")


def known_and_unmasked(s: Scenario, kind: str, normalised: str) -> None:
    @s.check("2", "real campaign is KNOWN_SCAM")
    def _check_4(c: Client, o: Outcome) -> None:
        body = lookup(c, kind, normalised)
        if body["verdict"] != "KNOWN_SCAM":
            raise AssertionError(
                f"{body['verdict']} with {body['distinct_reporters']} reporters,"
                f" {body['report_count']} reports"
            )

    @s.check("4", "shown in full at 3 or more reporters, masked below")
    def _check_5(c: Client, o: Outcome) -> None:
        body = lookup(c, kind, normalised)
        want = normalised if body["distinct_reporters"] >= 3 else masked_like(kind, normalised)
        if body["display_value"] != want:
            raise AssertionError(
                f"display_value {body['display_value']!r} with"
                f" {body['distinct_reporters']} reporters, want {want!r}"
            )


def accepted(s: Scenario) -> None:
    @s.check("2", "every report accepted")
    def _check_6(c: Client, o: Outcome) -> None:
        bad = [code for code in o.statuses if code != 201]
        if bad:
            raise AssertionError(f"{len(bad)} reports refused: {sorted(set(bad))}")
