"""Builds /map clusters from counted reports: window, radius, top scam type, severity bands.

Clusters always sit at the area's Appendix B point, never at anything a reporter sent.

Owner: B. Filled in by: B6.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.areas import Area, areas, distance_km

Severity = Literal["CRIT", "HIGH", "MED"]

# Counted reports in the window at or above which an area is CRIT or HIGH; below is MED.
CRIT_FROM = 10
HIGH_FROM = 5


@dataclass(frozen=True)
class AreaCount:
    count: int
    top_scam_type: str


@dataclass(frozen=True)
class Cluster:
    area: Area
    count: int
    top_scam_type: str
    severity: Severity


def severity(count: int) -> Severity:
    if count >= CRIT_FROM:
        return "CRIT"
    if count >= HIGH_FROM:
        return "HIGH"
    return "MED"


def areas_within(centre: str, radius_km: float) -> list[str]:
    """Every known area whose point is within radius_km of the centre's point (inclusive)."""
    return [p for p in areas() if distance_km(centre, p) <= radius_km]


def clusters(counts: dict[str, AreaCount]) -> list[Cluster]:
    """One cluster per area with at least one counted report, busiest first."""
    found = [
        Cluster(areas()[p], c.count, c.top_scam_type, severity(c.count))
        for p, c in counts.items()
        if c.count > 0
    ]
    return sorted(found, key=lambda c: (-c.count, c.area.pincode))
