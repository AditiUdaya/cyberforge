"""Scores a run against the PRD rubric; lists every failing scenario with its seed.

Per family: the share of scenarios where every check passed, against the SPEC threshold.
Per PRD row: points times the share of that row's checks that passed. This is an estimate of
what the judges' tool would see, not their scoring; rows 6 and 7 are judged by people.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

from families import THRESHOLDS
from generator import Scenario

ROWS: dict[str, tuple[str, int]] = {
    "1": ("Stops fake reports", 20),
    "2": ("Lookup gives the right answer", 15),
    "3": ("Map and alerts", 10),
    "4": ("Privacy", 15),
    "5": ("Server and licence", 15),
    "bonus:verified": ("Bonus: verified numbers", 3),
    "bonus:dispute": ("Bonus: disputes", 2),
    "bonus:fakes": ("Bonus: fakes never alert", 2),
}
NOT_MEASURED = {
    "2": "load latency: perf.py",
    "4": "full privacy scan: python -m scanners.all",
    "5": "only 'licence survives reset'; the demo is scripts/license_demo.sh",
}
SHOW_FAILURES = 25


@dataclass(frozen=True)
class CheckResult:
    row: str
    label: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ScenarioResult:
    family: str
    seed: int
    salt: str
    variant: str
    checks: tuple[CheckResult, ...]

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @classmethod
    def from_checks(cls, s: Scenario, checks: list[CheckResult]) -> ScenarioResult:
        return cls(s.family, s.seed, s.salt, s.variant, tuple(checks))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"passed": self.passed}


def family_rates(results: list[ScenarioResult]) -> dict[str, tuple[int, int]]:
    rates: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in results:
        rates[r.family][0] += r.passed
        rates[r.family][1] += 1
    return {f: (p, n) for f, (p, n) in rates.items()}


def failing_thresholds(results: list[ScenarioResult]) -> list[str]:
    return [
        f
        for f, (passed, total) in family_rates(results).items()
        if total and passed / total < THRESHOLDS[f]
    ]


def row_estimates(results: list[ScenarioResult]) -> dict[str, tuple[float, int, int]]:
    """row -> (estimated points, checks passed, checks run)."""
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in results:
        for c in r.checks:
            counts[c.row][0] += c.passed
            counts[c.row][1] += 1
    out = {}
    for row, (passed, total) in counts.items():
        points = ROWS[row][1]
        out[row] = (points * passed / total if total else 0.0, passed, total)
    return out


def render(results: list[ScenarioResult], *, seeds_name: str, salt: str, seconds: float) -> str:
    lines = [
        f"\nScorecard: {len(results)} scenarios, seeds {seeds_name}, salt {salt}, {seconds:.0f}s"
    ]

    lines.append("\nFamily   passed      rate   need   ")
    failing = set(failing_thresholds(results))
    for family, (passed, total) in family_rates(results).items():
        mark = "FAIL" if family in failing else "ok"
        rate, need = passed / total, THRESHOLDS[family]
        lines.append(f"{family:<8} {passed:>3}/{total:<5} {rate:6.0%} {need:6.0%}   {mark}")

    lines.append("\nPRD row                              estimate   checks")
    estimates = row_estimates(results)
    total_points = 0.0
    for row, (title, points) in ROWS.items():
        if row not in estimates:
            continue
        got, passed, total = estimates[row]
        total_points += got
        note = f"   ({NOT_MEASURED[row]})" if row in NOT_MEASURED else ""
        lines.append(f"{title:<36} {got:5.1f}/{points:<3} {passed:>4}/{total}{note}")
    lines.append(f"{'Measured total':<36} {total_points:5.1f}")
    lines.append("Rows 6 (easy to report) and 7 (demo and code) are judged by people.")

    failures = [(r, c) for r in results for c in r.checks if not c.passed]
    if failures:
        lines.append(
            f"\nFailing checks: {len(failures)} (first {SHOW_FAILURES}; replay with --replay)"
        )
        for r, c in failures[:SHOW_FAILURES]:
            lines.append(
                f"  {r.family}:{r.seed} [{r.variant}] {c.label}: {c.detail[:160]}"
                f"\n      replay: --replay {r.family}:{r.seed} --salt {r.salt}"
            )
    lines.append(
        "\nThresholds: "
        + ("all met" if not failing else f"not met for {', '.join(sorted(failing))}")
    )
    return "\n".join(lines)
