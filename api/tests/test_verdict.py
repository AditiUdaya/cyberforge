"""Verdict rules: verified wins, NO_REPORTS, SUSPICIOUS, KNOWN_SCAM thresholds, challenge cap.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

from app.core.trust_config import KNOWN_SCAM_MIN_CLUSTERS, KNOWN_SCAM_MIN_SCORE
from app.core.verdict import CaseFacts, verdict


def facts(
    reports: int = 0, clusters: int = 0, score: float = 0.0, challenged: bool = False
) -> CaseFacts:
    return CaseFacts(
        report_count=reports, clusters=clusters, weighted_score=score, challenged=challenged
    )


def test_no_reports() -> None:
    assert verdict(facts(), verified=False) == "NO_REPORTS"


def test_verified_wins_over_any_reports() -> None:
    assert verdict(facts(), verified=True) == "VERIFIED_BUSINESS"
    assert verdict(facts(40, 40, 40.0), verified=True) == "VERIFIED_BUSINESS"


def test_any_accepted_report_is_suspicious() -> None:
    assert verdict(facts(1, 1, 1.0), verified=False) == "SUSPICIOUS"
    assert verdict(facts(6, 1, 1.0), verified=False) == "SUSPICIOUS"


def test_known_scam_needs_clusters_and_score() -> None:
    n = KNOWN_SCAM_MIN_CLUSTERS
    s = KNOWN_SCAM_MIN_SCORE
    assert verdict(facts(n, n, s), verified=False) == "KNOWN_SCAM"
    assert verdict(facts(n, n - 1, s), verified=False) == "SUSPICIOUS"
    assert verdict(facts(n, n, s - 0.1), verified=False) == "SUSPICIOUS"


def test_challenge_caps_at_suspicious() -> None:
    assert verdict(facts(10, 10, 10.0, challenged=True), verified=False) == "SUSPICIOUS"
