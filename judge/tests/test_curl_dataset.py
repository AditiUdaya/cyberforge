"""The curl script for a dataset: one plain curl per request, safe quoting, status checks.

Owner: B. Filled in by: B9.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from curl_dataset import generate
from score_dataset import read_status_log, status_results

DATASETS = sorted((Path(__file__).resolve().parents[1] / "datasets").glob("*.json"))
BASH = shutil.which("bash")
needs_bash = pytest.mark.skipif(BASH is None, reason="bash is not available")

TRICKY_NOTE = 'It\'s "quoted", has a \\ backslash, $HOME, `date`, $(id), and हिंदी में भी; rm -rf /'
REPORT: dict[str, Any] = {
    "report_id": "rep_1",
    "occurred_at": "2026-10-31T10:00:00+05:30",
    "reported_at": "2026-10-31T10:30:00+05:30",
    "reporter_id": "r_1",
    "ip_prefix": "10.1.1",
    "channel": "Phone call",
    "scam_type": "digital-arrest",
    "identifier_type": "phone",
    "identifier_value": "+91 98765 43210",
    "pincode": "560102",
    "note": TRICKY_NOTE,
}
DOC: dict[str, Any] = {
    "_anchor": "2026-10-31T12:00:00+00:00",
    "reports": [
        REPORT,
        REPORT | {"report_id": "junk_1", "identifier_value": "12345"},
        REPORT | {"report_id": "spam_1"},
    ],
    "expect_status": {"junk_1": [400], "spam_1": [201, 429]},
    "challenges": [
        {
            "identifier_type": "phone",
            "identifier_value": "+91 80 4100 2233",
            "claimant_name": "Fresh Bakes",
            "contact_email": "owner@example.com",
            "proof_note": "GST certificate",
        }
    ],
    "challenge_status": [[201]],
    "expect": [],
}


def run(
    script: str, tmp_path: Path, status: str = "201", env: dict[str, str] | None = None
) -> tuple[int, str, list[str]]:
    """Run the script with `curl` replaced by a function that records the body it was given."""
    capture = tmp_path / "bodies.txt"
    fake = tmp_path / "fake.sh"
    fake.write_text(
        'curl() {\n  local body=""\n  while [ $# -gt 0 ]; do\n'
        '    case "$1" in -d) body="$2"; shift ;; esac; shift\n  done\n'
        '  printf "%s\\n" "$body" >> "$CAPTURE"\n  printf "%s" "$FAKE_STATUS"\n}\n',
        encoding="utf-8",
        newline="\n",
    )
    path = tmp_path / "load.sh"
    path.write_bytes(script.encode("utf-8"))
    assert BASH is not None
    done = subprocess.run(
        [BASH, path.as_posix(), "http://example.test"],
        env=os.environ
        | {"BASH_ENV": fake.as_posix(), "CAPTURE": capture.as_posix(), "FAKE_STATUS": status}
        | (env or {}),
        capture_output=True,
        timeout=60,
        check=False,
    )
    bodies = capture.read_text(encoding="utf-8").splitlines() if capture.exists() else []
    return done.returncode, done.stdout.decode("utf-8", "replace"), bodies


def test_one_curl_per_report_and_dispute() -> None:
    script = generate(DOC, timedelta(0))
    lines = [line for line in script.splitlines() if line.startswith("code=$(curl ")]
    assert len(lines) == 4
    assert sum('"$BASE/reports"' in line for line in lines) == 3
    assert sum('"$BASE/challenges"' in line for line in lines) == 1
    assert all("-X POST" in line and "content-type: application/json" in line for line in lines)


def test_the_script_is_plain_ascii_with_unix_line_endings() -> None:
    script = generate(DOC, timedelta(0))
    assert script.isascii()
    assert "\r" not in script
    assert script.startswith("#!/usr/bin/env bash\n")


@needs_bash
def test_the_script_is_valid_bash(tmp_path: Path) -> None:
    path = tmp_path / "load.sh"
    path.write_bytes(generate(DOC, timedelta(0)).encode())
    assert BASH is not None
    assert subprocess.run([BASH, "-n", path.as_posix()], check=False).returncode == 0


@needs_bash
def test_every_body_arrives_exactly_as_the_dataset_has_it(tmp_path: Path) -> None:
    _, _, bodies = run(generate(DOC, timedelta(0)), tmp_path)
    assert [json.loads(b) for b in bodies] == [*DOC["reports"], *DOC["challenges"]]
    assert json.loads(bodies[0])["note"] == TRICKY_NOTE


@needs_bash
def test_an_unexpected_status_is_reported_and_fails_the_script(tmp_path: Path) -> None:
    code, out, _ = run(generate(DOC, timedelta(0)), tmp_path, status="201")
    assert code != 0
    assert "junk_1: got 201, wanted 400" in out
    assert "spam_1" not in out and "rep_1:" not in out
    assert "4 requests sent, 1 with an unexpected status" in out


@needs_bash
def test_when_every_status_is_expected_the_script_succeeds(tmp_path: Path) -> None:
    only_valid = DOC | {
        "reports": [REPORT],
        "expect_status": {},
        "challenges": [],
        "challenge_status": [],
    }
    code, out, bodies = run(generate(only_valid, timedelta(0)), tmp_path)
    assert code == 0 and len(bodies) == 1
    assert "1 requests sent, 0 with an unexpected status" in out


@needs_bash
def test_times_move_forward_by_the_shift_and_keep_their_offset(tmp_path: Path) -> None:
    _, _, bodies = run(generate(DOC, timedelta(days=3, hours=2)), tmp_path)
    first = json.loads(bodies[0])
    assert first["occurred_at"] == "2026-11-03T12:00:00+05:30"
    assert first["reported_at"] == "2026-11-03T12:30:00+05:30"
    assert datetime.fromisoformat(first["occurred_at"]).utcoffset() == timedelta(
        hours=5, minutes=30
    )


@needs_bash
def test_every_status_is_logged_for_scoring(tmp_path: Path) -> None:
    log = tmp_path / "status.tsv"
    run(generate(DOC, timedelta(0)), tmp_path, env={"STATUS_LOG": log.as_posix()})
    assert log.read_text(encoding="utf-8").splitlines() == [
        "201\trep_1",
        "201\tjunk_1",
        "201\tspam_1",
        "201\tdispute 1",
    ]


def test_the_status_log_is_scored_like_the_python_client_scores_replies(tmp_path: Path) -> None:
    log = tmp_path / "status.tsv"
    log.write_text("201\trep_1\n400\tjunk_1\n429\tspam_1\n201\tdispute 1\n", encoding="utf-8")
    results = status_results(DOC, *read_status_log(log))
    assert [r.passed for r in results] == [True, True, True]
    assert [r.row for r in results] == ["2", "1", "bonus:dispute"]

    log.write_text("201\trep_1\n201\tjunk_1\n201\tspam_1\n429\tdispute 1\n", encoding="utf-8")
    wrong = status_results(DOC, *read_status_log(log))
    assert [r.passed for r in wrong] == [True, False, False]
    assert "junk_1: 201, want [400]" in wrong[1].detail


def test_a_request_that_never_got_a_status_counts_as_a_failure(tmp_path: Path) -> None:
    log = tmp_path / "status.tsv"
    log.write_text("201\trep_1\n", encoding="utf-8")
    results = status_results(DOC, *read_status_log(log))
    assert [r.passed for r in results] == [True, False, False]


@pytest.mark.parametrize("path", DATASETS, ids=lambda p: p.stem)
def test_every_real_dataset_becomes_a_script(path: Path) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    anchor = datetime.fromisoformat(doc["_anchor"])
    script = generate(doc, datetime.now(UTC) - anchor)
    lines = [line for line in script.splitlines() if line.startswith("code=$(curl ")]
    assert len(lines) == len(doc["reports"]) + len(doc["challenges"])
    assert script.isascii() and "\r" not in script
