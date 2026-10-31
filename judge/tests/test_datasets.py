"""The evaluation datasets use the PRD Appendix A schema and shift in time without changing shape.

Owner: B. Filled in by: B9.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from score_dataset import shift

HERE = Path(__file__).resolve().parents[1]
CONTRACT = HERE.parent / "shared" / "contract"
DATASETS = sorted((HERE / "datasets").glob("*.json"))
KINDS = {"lookup", "lookup_status", "same_answer", "map", "alerts", "severity"}
ROWS = {"1", "2", "3", "4", "5", "bonus:verified", "bonus:dispute", "bonus:fakes"}


def schema(name: str) -> Draft202012Validator:
    return Draft202012Validator(
        json.loads((CONTRACT / f"{name}.schema.json").read_text(encoding="utf-8"))
    )


def load(path: Path) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return doc


def test_there_are_five_datasets() -> None:
    assert [p.stem[:2] for p in DATASETS] == ["01", "02", "03", "04", "05"]


@pytest.mark.parametrize("path", DATASETS, ids=lambda p: p.stem)
def test_every_accepted_report_is_a_prd_report(path: Path) -> None:
    doc = load(path)
    reports = schema("reports.request")
    ids = [b["report_id"] for b in doc["reports"]]
    assert len(ids) == len(set(ids)), "report_id must be unique within a dataset"
    for body in doc["reports"]:
        if body["report_id"] in doc["expect_status"]:
            continue
        assert not list(reports.iter_errors(body)), body["report_id"]
        assert set(body) == {
            "report_id",
            "occurred_at",
            "reported_at",
            "reporter_id",
            "ip_prefix",
            "channel",
            "scam_type",
            "identifier_type",
            "identifier_value",
            "pincode",
            "locality",
            "city",
            "note",
            "has_screenshot",
            "amount_lost_inr",
        }


@pytest.mark.parametrize("path", DATASETS, ids=lambda p: p.stem)
def test_disputes_are_prd_challenges(path: Path) -> None:
    doc = load(path)
    challenges = schema("challenges.request")
    for body in doc["challenges"]:
        assert not list(challenges.iter_errors(body))
    assert len(doc["challenges"]) == len(doc["challenge_status"])


@pytest.mark.parametrize("path", DATASETS, ids=lambda p: p.stem)
def test_expectations_are_well_formed(path: Path) -> None:
    doc = load(path)
    assert doc["expect"]
    for e in doc["expect"]:
        assert e["kind"] in KINDS and e["row"] in ROWS and e["label"]
    for codes in doc["expect_status"].values():
        assert set(codes) <= {400, 429}


def test_the_datasets_cover_every_scored_row_and_edge() -> None:
    every = [e for p in DATASETS for e in load(p)["expect"]]
    assert {e["row"] for e in every} >= {
        "1",
        "2",
        "3",
        "4",
        "bonus:verified",
        "bonus:dispute",
        "bonus:fakes",
    }
    statuses = [c for p in DATASETS for codes in load(p)["expect_status"].values() for c in codes]
    assert 400 in statuses and 429 in statuses
    types = {b["identifier_type"] for p in DATASETS for b in load(p)["reports"]}
    assert {"phone", "upi", "url", "sender_id"} <= types


def test_shift_keeps_offsets_and_gaps() -> None:
    body = {"occurred_at": "2026-10-27T18:21:04+05:30", "reported_at": "2026-10-27T12:51:04+00:00"}
    moved = shift(body, timedelta(days=2, hours=3))
    assert moved["occurred_at"] == "2026-10-29T21:21:04+05:30"
    assert moved["reported_at"] == "2026-10-29T15:51:04+00:00"
    gap = datetime.fromisoformat(moved["reported_at"]) - datetime.fromisoformat(
        moved["occurred_at"]
    )
    assert gap == timedelta(0)


def test_shift_leaves_junk_times_alone() -> None:
    body = {"occurred_at": "yesterday", "reported_at": "2026-10-27T18:21:04"}
    moved = shift(body, timedelta(days=1))
    assert moved["occurred_at"] == "yesterday"
    assert moved["reported_at"] == "2026-10-28T18:21:04"
