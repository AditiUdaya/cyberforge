"""Verdict from case state: VERIFIED_BUSINESS, KNOWN_SCAM, SUSPICIOUS or NO_REPORTS.
Challenge caps at SUSPICIOUS. Thresholds read from trust_config (B5).

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.trust_config import KNOWN_SCAM_MIN_CLUSTERS, KNOWN_SCAM_MIN_SCORE

Verdict = Literal["KNOWN_SCAM", "SUSPICIOUS", "NO_REPORTS", "VERIFIED_BUSINESS"]


@dataclass(frozen=True)
class CaseFacts:
    report_count: int
    clusters: int
    weighted_score: float
    challenged: bool


def verdict(facts: CaseFacts, *, verified: bool) -> Verdict:
    if verified:
        return "VERIFIED_BUSINESS"
    if facts.report_count == 0:
        return "NO_REPORTS"
    if (
        not facts.challenged
        and facts.clusters >= KNOWN_SCAM_MIN_CLUSTERS
        and facts.weighted_score >= KNOWN_SCAM_MIN_SCORE
    ):
        return "KNOWN_SCAM"
    return "SUSPICIOUS"
