"""SQL for reports and cases: the only module that reads or writes those tables.

Every value passed in is already validated, normalised and, for identifiers and reporter
fields, a keyed HMAC.

Owner: B. Filled in by: B2 (storage), B5 (trust rules).
"""

from __future__ import annotations

import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from app.core.trust import ReportFacts, assess
from app.core.trust_config import RATE_LIMIT_WINDOW


@dataclass(frozen=True)
class NewReport:
    report_id: str
    identifier_type: str
    identifier_hmac: str
    reporter_hmac: str
    ip_prefix_hmac: str
    channel: str
    scam_type: str
    pincode: str
    occurred_at: str
    reported_at: str
    note_length: int
    note_sketch: bytes
    has_screenshot: bool
    amount_lost_inr: float
    origin: str


@dataclass(frozen=True)
class CaseRow:
    case_id: str
    report_count: int
    distinct_reporters: int
    weighted_score: float
    first_seen: str | None
    last_seen: str | None
    top_scam_type: str | None
    challenged: bool


@dataclass(frozen=True)
class EvidenceRow:
    occurred_at: str
    channel: str
    scam_type: str
    pincode: str


def add_report(conn: sqlite3.Connection, report: NewReport) -> tuple[str, bool]:
    """Store a report under its identifier's case. Returns (case_id, merged)."""
    row = conn.execute(
        "SELECT case_id FROM cases WHERE identifier_type = ? AND identifier_hmac = ?",
        (report.identifier_type, report.identifier_hmac),
    ).fetchone()
    merged = row is not None
    case_id = str(row["case_id"]) if row is not None else f"case_{secrets.token_hex(8)}"
    if not merged:
        conn.execute(
            "INSERT INTO cases (case_id, identifier_type, identifier_hmac) VALUES (?, ?, ?)",
            (case_id, report.identifier_type, report.identifier_hmac),
        )
    first_time = (
        conn.execute(
            "SELECT 1 FROM reports WHERE reporter_hmac = ? AND reported_at < ? LIMIT 1",
            (report.reporter_hmac, report.reported_at),
        ).fetchone()
        is None
    )
    conn.execute(
        "INSERT INTO reports (report_id, case_id, reporter_hmac, ip_prefix_hmac, channel,"
        " scam_type, pincode, occurred_at, reported_at, note_length, note_sketch,"
        " has_screenshot, amount_lost_inr, origin, first_time)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            report.report_id,
            case_id,
            report.reporter_hmac,
            report.ip_prefix_hmac,
            report.channel,
            report.scam_type,
            report.pincode,
            report.occurred_at,
            report.reported_at,
            report.note_length,
            report.note_sketch,
            int(report.has_screenshot),
            report.amount_lost_inr,
            report.origin,
            int(first_time),
        ),
    )
    _recompute(conn, case_id)
    return case_id, merged


def recent_reports(conn: sqlite3.Connection, reporter_hmac: str, reported_at: datetime) -> int:
    """How many reports this reporter made within the rate-limit window around this one."""
    low = (reported_at - RATE_LIMIT_WINDOW).isoformat()
    high = (reported_at + RATE_LIMIT_WINDOW).isoformat()
    row = conn.execute(
        "SELECT COUNT(*) FROM reports WHERE reporter_hmac = ? AND reported_at > ?"
        " AND reported_at < ?",
        (reporter_hmac, low, high),
    ).fetchone()
    return int(row[0])


def _recompute(conn: sqlite3.Connection, case_id: str) -> None:
    """Re-run the trust rules over the whole case and refresh what a lookup reads."""
    rows = conn.execute(
        "SELECT id, reporter_hmac, ip_prefix_hmac, reported_at, occurred_at, note_length,"
        " note_sketch, first_time FROM reports WHERE case_id = ?",
        (case_id,),
    ).fetchall()
    result = assess(
        [
            ReportFacts(
                id=int(r["id"]),
                reporter=str(r["reporter_hmac"]),
                ip=str(r["ip_prefix_hmac"]),
                reported_at=datetime.fromisoformat(r["reported_at"]),
                occurred_at=datetime.fromisoformat(r["occurred_at"]),
                note_length=int(r["note_length"]),
                sketch=bytes(r["note_sketch"]),
                first_time=bool(r["first_time"]),
            )
            for r in rows
        ]
    )
    conn.executemany(
        "UPDATE reports SET status = ?, cluster_id = ?, weight = ? WHERE id = ?",
        [
            (result.statuses[rid], result.cluster_of[rid], result.weight_of[rid], rid)
            for rid in result.statuses
        ],
    )
    span = conn.execute(
        "SELECT COUNT(*) AS n, MIN(occurred_at) AS first, MAX(occurred_at) AS last"
        " FROM reports WHERE case_id = ?",
        (case_id,),
    ).fetchone()
    top = conn.execute(
        "SELECT scam_type FROM reports WHERE case_id = ? GROUP BY scam_type"
        " ORDER BY COUNT(*) DESC, MAX(occurred_at) DESC LIMIT 1",
        (case_id,),
    ).fetchone()
    conn.execute(
        "UPDATE cases SET report_count = ?, distinct_reporters = ?, weighted_score = ?,"
        " first_seen = ?, last_seen = ?, top_scam_type = ? WHERE case_id = ?",
        (
            span["n"],
            result.clusters,
            result.score,
            span["first"],
            span["last"],
            top["scam_type"] if top is not None else None,
            case_id,
        ),
    )


def find_case(
    conn: sqlite3.Connection, identifier_type: str, identifier_hmac: str
) -> CaseRow | None:
    row = conn.execute(
        "SELECT case_id, report_count, distinct_reporters, weighted_score, first_seen,"
        " last_seen, top_scam_type, challenged FROM cases"
        " WHERE identifier_type = ? AND identifier_hmac = ?",
        (identifier_type, identifier_hmac),
    ).fetchone()
    if row is None:
        return None
    return CaseRow(
        case_id=str(row["case_id"]),
        report_count=int(row["report_count"]),
        distinct_reporters=int(row["distinct_reporters"]),
        weighted_score=float(row["weighted_score"]),
        first_seen=row["first_seen"],
        last_seen=row["last_seen"],
        top_scam_type=row["top_scam_type"],
        challenged=bool(row["challenged"]),
    )


def evidence(conn: sqlite3.Connection, case_id: str, limit: int) -> list[EvidenceRow]:
    rows = conn.execute(
        "SELECT occurred_at, channel, scam_type, pincode FROM reports WHERE case_id = ?"
        " ORDER BY occurred_at DESC LIMIT ?",
        (case_id, limit),
    ).fetchall()
    return [
        EvidenceRow(
            occurred_at=str(r["occurred_at"]),
            channel=str(r["channel"]),
            scam_type=str(r["scam_type"]),
            pincode=str(r["pincode"]),
        )
        for r in rows
    ]


def reset(conn: sqlite3.Connection) -> None:
    """Delete every report and case. Reference data and the licence are kept."""
    conn.execute("DELETE FROM reports")
    conn.execute("DELETE FROM cases")
