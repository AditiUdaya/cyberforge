"""Trust rules: reporter and connection clustering, copied-note merging, coordinated-burst cap,
weights, and report status counted / merged / suspect.

Pure: takes every report about one identifier and returns the case's assessment. The store
re-runs it after each new report, so a burst found later also re-labels earlier reports.
Rules and thresholds: ARCHITECTURE.md "Trust rules" and trust_config.py.

Owner: B. Filled in by: B5.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.core.notes import similarity
from app.core.trust_config import (
    BURST_INCIDENT_SPAN,
    BURST_MAX_WEIGHT,
    BURST_MIN_REPORTS,
    BURST_MOSTLY,
    BURST_WINDOW,
    NOTE_DUPLICATE_SIMILARITY,
    OWN_WORDS_MIN_CHARS,
    SAME_CONNECTION_WINDOW,
    WEIGHT_OWN_WORDS,
    WEIGHT_SHORT_NOTE,
)

Status = Literal["counted", "merged", "suspect"]


@dataclass(frozen=True)
class ReportFacts:
    """What the trust rules may see about one stored report: digests and times, no raw data."""

    id: int
    reporter: str
    ip: str
    reported_at: datetime
    occurred_at: datetime
    note_length: int
    sketch: bytes
    first_time: bool


@dataclass(frozen=True)
class Assessment:
    statuses: dict[int, Status]
    cluster_of: dict[int, int]
    weight_of: dict[int, float]
    clusters: int
    score: float


def assess(reports: Sequence[ReportFacts]) -> Assessment:
    if not reports:
        return Assessment({}, {}, {}, 0, 0.0)
    ordered = sorted(reports, key=lambda r: (r.reported_at, r.id))
    root = _cluster(ordered)
    suspect = _burst_members(ordered)

    members: dict[int, list[ReportFacts]] = defaultdict(list)
    for r in ordered:
        members[root[r.id]].append(r)

    statuses: dict[int, Status] = {}
    weight_of: dict[int, float] = {r.id: 0.0 for r in ordered}
    independent = 0
    score = 0.0
    burst_weight = 0.0
    burst_reports: list[int] = []
    for group in members.values():
        weight = _cluster_weight(group)
        clean = [r for r in group if r.id not in suspect]
        if not clean:
            burst_weight += weight
            burst_reports.extend(r.id for r in group)
            for r in group:
                statuses[r.id] = "suspect"
            continue
        independent += 1
        score += weight
        weight_of[clean[0].id] = weight
        statuses[clean[0].id] = "counted"
        for r in group:
            if r.id != clean[0].id:
                statuses[r.id] = "suspect" if r.id in suspect else "merged"

    if burst_reports:
        independent += 1
        capped = min(burst_weight, BURST_MAX_WEIGHT)
        score += capped
        for rid in burst_reports:
            weight_of[rid] = capped / len(burst_reports)

    return Assessment(statuses, root, weight_of, independent, round(score, 6))


def _cluster(ordered: Sequence[ReportFacts]) -> dict[int, int]:
    """Union-find: same reporter, same connection within a day, or near-identical notes."""
    parent = {r.id: r.id for r in ordered}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    by_reporter: dict[str, int] = {}
    last_on_ip: dict[str, ReportFacts] = {}
    with_notes: list[ReportFacts] = []
    for r in ordered:
        if r.reporter in by_reporter:
            union(by_reporter[r.reporter], r.id)
        else:
            by_reporter[r.reporter] = r.id
        previous = last_on_ip.get(r.ip)
        if previous is not None and r.reported_at - previous.reported_at <= SAME_CONNECTION_WINDOW:
            union(previous.id, r.id)
        last_on_ip[r.ip] = r
        if r.sketch:
            for other in with_notes:
                if similarity(r.sketch, other.sketch) >= NOTE_DUPLICATE_SIMILARITY:
                    union(other.id, r.id)
            with_notes.append(r)
    return {r.id: find(r.id) for r in ordered}


def _burst_members(ordered: Sequence[ReportFacts]) -> set[int]:
    """First-time reporters arriving together who look coordinated (rule 4)."""
    fresh = [r for r in ordered if r.first_time]
    suspect: set[int] = set()
    start = 0
    for end in range(len(fresh)):
        while fresh[end].reported_at - fresh[start].reported_at > BURST_WINDOW:
            start += 1
        window = fresh[start : end + 1]
        if len(window) >= BURST_MIN_REPORTS and _coordinated(window):
            suspect.update(r.id for r in window)
    return suspect


def _coordinated(window: Sequence[ReportFacts]) -> bool:
    incidents = [r.occurred_at for r in window]
    if max(incidents) - min(incidents) <= BURST_INCIDENT_SPAN:
        return True
    weak = 0
    for i, r in enumerate(window):
        if r.note_length < OWN_WORDS_MIN_CHARS or any(
            similarity(r.sketch, o.sketch) >= NOTE_DUPLICATE_SIMILARITY
            for j, o in enumerate(window)
            if j != i
        ):
            weak += 1
    return weak >= BURST_MOSTLY * len(window)


def _cluster_weight(group: Sequence[ReportFacts]) -> float:
    own_words = any(r.note_length >= OWN_WORDS_MIN_CHARS for r in group)
    return WEIGHT_OWN_WORDS if own_words else WEIGHT_SHORT_NOTE
