"""Generator and families: deterministic per seed, PRD-valid bodies, realistic people and notes.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from families import FAMILIES
from generator import Gen, areas, jaccard, phone_formats

REPO = Path(__file__).resolve().parents[2]
REPORT_SCHEMA = json.loads(
    (REPO / "shared" / "contract" / "reports.request.schema.json").read_text(encoding="utf-8")
)
NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
SEEDS = range(1, 11)
# The trust rules treat notes at 0.8 similarity as copied. Real people must stay at least 0.1
# below that. Measured on 31 Oct (English notes): max 0.64, p99 0.57 over 1,000 campaigns.
COPY_MARGIN = 0.7


def test_every_family_in_the_spec_is_present() -> None:
    spec = "T1 T2 T3 T4 T5 R1 R2 R3 F1 M1 A1 A2 A3 C1 Z1"
    assert list(FAMILIES) == spec.split()


@pytest.mark.parametrize("family", list(FAMILIES))
def test_same_seed_and_salt_give_the_same_scenario(family: str) -> None:
    a = FAMILIES[family](Gen(family, 7, "salt", NOW))
    b = FAMILIES[family](Gen(family, 7, "salt", NOW))
    c = FAMILIES[family](Gen(family, 7, "other-salt", NOW))
    assert a.reports == b.reports
    assert a.variant == b.variant
    assert a.reports != c.reports or not a.reports


@pytest.mark.parametrize("family", [f for f in FAMILIES if f != "T4"])
@pytest.mark.parametrize("seed", SEEDS)
def test_report_bodies_follow_the_prd_contract(family: str, seed: int) -> None:
    scenario = FAMILIES[family](Gen(family, seed, "s", NOW))
    validator = Draft202012Validator(REPORT_SCHEMA)
    for step in scenario.reports:
        assert not list(validator.iter_errors(step.body)), step.body
        occurred = datetime.fromisoformat(step.body["occurred_at"])
        reported = datetime.fromisoformat(step.body["reported_at"])
        assert occurred.utcoffset() is not None
        assert occurred <= reported <= NOW
        assert step.body["pincode"] in areas()


@pytest.mark.parametrize("seed", SEEDS)
def test_real_campaign_people_are_unrelated(seed: int) -> None:
    scenario = FAMILIES["R1"](Gen("R1", seed, "s", NOW))
    bodies = [s.body for s in scenario.reports]
    assert len({b["reporter_id"] for b in bodies}) == len(bodies)
    assert len({b["ip_prefix"] for b in bodies}) == len(bodies)
    notes = [b["note"] for b in bodies]
    worst = max((jaccard(a, b) for i, a in enumerate(notes) for b in notes[i + 1 :]), default=0.0)
    assert worst < COPY_MARGIN, f"two real reporters wrote near-identical notes ({worst:.2f})"


@pytest.mark.parametrize("seed", SEEDS)
def test_bombing_is_within_an_hour_and_coordinated(seed: int) -> None:
    scenario = FAMILIES["T1"](Gen("T1", seed, "s", NOW))
    times = [datetime.fromisoformat(s.body["reported_at"]) for s in scenario.reports]
    assert len(times) == 40
    assert max(times) - min(times) <= timedelta(hours=1)


def test_t4_junk_is_all_expected_400() -> None:
    scenario = FAMILIES["T4"](Gen("T4", 1, "s", NOW))
    assert scenario.reports
    assert all(step.expect == {400} for step in scenario.reports)


def test_phone_formats_are_distinct_spellings_of_one_number() -> None:
    number = Gen("F1", 3, "s", NOW).mobile()
    formats = phone_formats(number)
    assert len(set(formats)) == len(formats) >= 4
    for spelled in formats:
        assert "".join(ch for ch in spelled if ch.isdigit()).endswith(number)
