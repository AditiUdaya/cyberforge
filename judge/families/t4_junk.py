"""T4 Junk: 12345, test, empty, malformed values, wrong type, unknown pincode, bad or future time.
Expected: 400; nothing stored.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from datetime import timedelta

from contract import Client
from generator import Gen, Outcome, ReportStep, Scenario, lookup


def generate(g: Gen) -> Scenario:
    s = g.scenario("all junk kinds")
    real = g.mobile()
    base = g.report(g.person(), "phone", f"+91 {real}", occurred=g.ago(hours=3)).body
    future = (g.now + timedelta(days=g.rng.randint(1, 30))).isoformat()
    junk = [
        {"identifier_value": "12345"},
        {"identifier_value": "test"},
        {"identifier_value": ""},
        {"identifier_value": "98765"},
        {"identifier_type": "upi", "identifier_value": "ravi@@okaxis"},
        {"identifier_type": "upi", "identifier_value": "test"},
        {"identifier_type": "url", "identifier_value": "http://"},
        {"identifier_type": "url", "identifier_value": "not a link"},
        {"identifier_type": "sender_id", "identifier_value": "HDFC"},
        {"identifier_type": "upi", "identifier_value": f"+91 {real}"},
        {"pincode": "999999"},
        {"pincode": "HSR Layout"},
        {"occurred_at": "yesterday"},
        {"occurred_at": future},
        {"occurred_at": base["occurred_at"][:19]},
    ]
    for n, change in enumerate(junk):
        body = base | change | {"report_id": f"{base['report_id']}_j{n}"}
        s.reports.append(ReportStep(body, frozenset({400})))

    @s.check("1", "every junk report is 400")
    def _check_1(c: Client, o: Outcome) -> None:
        bad = [(i, code) for i, code in enumerate(o.statuses) if code != 400]
        if bad:
            raise AssertionError(f"accepted junk: {[junk[i] for i, _ in bad][:3]}")

    @s.check("1", "nothing stored")
    def _check_2(c: Client, o: Outcome) -> None:
        verdict = lookup(c, "phone", f"+91{real}")["verdict"]
        if verdict != "NO_REPORTS":
            raise AssertionError(f"junk was stored: {verdict}")

    return s
