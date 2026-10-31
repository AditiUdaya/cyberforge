"""Trust rules on synthetic reports: clustering, weights, the burst cap and report status.

Owner: B. Filled in by: B5.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.notes import sketch
from app.core.trust import ReportFacts, assess
from app.core.trust_config import (
    BURST_MAX_WEIGHT,
    WEIGHT_OWN_WORDS,
    WEIGHT_SHORT_NOTE,
)

KEY = b"k" * 32
T0 = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
OPENERS = ["Got a call", "My father received", "A woman phoned", "Someone rang", "A man called"]
CLAIMS = ["from the police", "about my KYC", "about a parcel", "offering a job", "about a refund"]


def own_words(n: int) -> str:
    return (
        f"{OPENERS[n % 5]} {CLAIMS[(n // 5) % 5]} on day {n}, number {n * 7919 % 1000}. "
        f"They asked for {n * 1234} rupees and said {'x' * (n % 7)} story {n} ends here {n * n}."
    )


def fact(
    n: int,
    *,
    reporter: str | None = None,
    ip: str | None = None,
    reported: timedelta = timedelta(0),
    occurred: timedelta | None = None,
    note: str | None = None,
    first_time: bool = True,
) -> ReportFacts:
    text = own_words(n) if note is None else note
    return ReportFacts(
        id=n,
        reporter=reporter or f"r{n}",
        ip=ip or f"ip{n}",
        reported_at=T0 + reported,
        occurred_at=T0 + (occurred if occurred is not None else reported - timedelta(hours=1)),
        note_length=len(text.strip()),
        sketch=sketch(text, KEY),
        first_time=first_time,
    )


def days(n: int) -> timedelta:
    return timedelta(days=n)


def test_unrelated_people_are_separate_clusters() -> None:
    result = assess([fact(n, reported=days(n)) for n in range(5)])
    assert result.clusters == 5
    assert result.score == 5 * WEIGHT_OWN_WORDS
    assert set(result.statuses.values()) == {"counted"}


def test_one_reporter_is_one_cluster_at_any_time_apart() -> None:
    result = assess([fact(n, reporter="same", reported=days(3 * n)) for n in range(4)])
    assert result.clusters == 1
    assert sorted(result.statuses.values()) == ["counted", "merged", "merged", "merged"]


def test_one_connection_within_24_hours_is_one_cluster() -> None:
    hours = [timedelta(hours=h) for h in (0, 5, 23)]
    result = assess([fact(n, ip="wifi", reported=h) for n, h in enumerate(hours)])
    assert result.clusters == 1


def test_one_connection_days_apart_is_separate() -> None:
    result = assess([fact(n, ip="office", reported=days(2 * n)) for n in range(3)])
    assert result.clusters == 3


def test_copied_notes_merge_across_people() -> None:
    script = own_words(99)
    result = assess([fact(n, note=script, reported=days(n)) for n in range(4)])
    assert result.clusters == 1


def test_short_notes_weigh_less() -> None:
    result = assess([fact(n, note="", reported=days(n)) for n in range(4)])
    assert result.clusters == 4
    assert result.score == 4 * WEIGHT_SHORT_NOTE


def test_coordinated_burst_with_empty_notes_is_capped_and_suspect() -> None:
    minutes = [timedelta(minutes=m * 1.4) for m in range(40)]
    spread = [timedelta(minutes=m * 9) for m in range(40)]
    reports = [
        fact(n, note="", reported=m, occurred=-s)
        for n, (m, s) in enumerate(zip(minutes, spread, strict=True))
    ]
    result = assess(reports)
    assert result.score <= BURST_MAX_WEIGHT
    assert result.clusters == 1
    assert set(result.statuses.values()) == {"suspect"}


def test_burst_with_bunched_incident_times_is_capped_even_with_own_words() -> None:
    reports = [
        fact(n, reported=timedelta(minutes=2 * n), occurred=-timedelta(minutes=30 - n % 10))
        for n in range(12)
    ]
    result = assess(reports)
    assert result.score <= BURST_MAX_WEIGHT
    assert result.clusters == 1


def test_real_sudden_wave_is_not_capped() -> None:
    reports = []
    for n in range(15):
        reported = timedelta(minutes=12 * n + 20)
        occurred = timedelta(minutes=12 * n)
        reports.append(fact(n, reported=reported, occurred=occurred))
    result = assess(reports)
    assert result.clusters == 15
    assert "suspect" not in result.statuses.values()


def test_returning_reporters_are_never_part_of_a_burst() -> None:
    reports = [fact(n, note="", reported=timedelta(minutes=n), first_time=False) for n in range(8)]
    result = assess(reports)
    assert "suspect" not in result.statuses.values()
    assert result.clusters == 8


def test_small_groups_are_not_bursts() -> None:
    reports = [fact(n, note="", reported=timedelta(minutes=n)) for n in range(3)]
    assert "suspect" not in assess(reports).statuses.values()


def test_burst_does_not_erase_earlier_real_reports() -> None:
    real = [fact(n, reported=-days(n + 1)) for n in range(3)]
    burst = [fact(100 + n, note="", reported=timedelta(minutes=n)) for n in range(10)]
    result = assess(real + burst)
    assert result.clusters == 4
    assert result.score == 3 * WEIGHT_OWN_WORDS + min(10 * WEIGHT_SHORT_NOTE, BURST_MAX_WEIGHT)
    assert [result.statuses[n] for n in range(3)] == ["counted"] * 3


def test_empty_case() -> None:
    result = assess([])
    assert (result.clusters, result.score, result.statuses) == (0, 0.0, {})
