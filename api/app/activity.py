"""The activity feed behind the website's live panel: what happened, never who.

Every accepted report, repeat, coordinated burst, rejection, rate limit, new known scam, dispute
and alert becomes an event. Identifiers appear only masked; no reporter or connection field is
ever recorded; rejections keep their reason, never the value sent. Repeats, bursts, rejections
and rate limits within an hour are grouped into one event whose count grows.

Owner: B. Filled in by: B9.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app import store
from app.core import alerts as alert_rules
from app.core.areas import areas
from app.core.mask import display_value
from app.core.normalise import IdentifierType
from app.core.validate import to_display, to_utc_text
from app.core.verdict import CaseFacts, verdict

GROUP_WINDOW = timedelta(hours=1)
FEED_LIMIT = 40


@dataclass(frozen=True)
class Context:
    """What an event may say about a report: area, type, channel and the masked identifier."""

    at: datetime
    pincode: str | None = None
    scam_type: str | None = None
    channel: str | None = None
    identifier_type: str | None = None
    display: str | None = None
    case_id: str | None = None


def masked(kind: IdentifierType, normalised: str) -> str:
    """Always the masked form, whatever the reporter count: events must never hold raw values."""
    return display_value(kind, normalised, 0)


def record(
    conn: sqlite3.Connection,
    kind: str,
    ctx: Context,
    *,
    detail: str | None = None,
    group: bool = False,
    count: int | None = None,
) -> None:
    """Add an event, or with group=True grow the matching one from the last hour."""
    at = to_utc_text(ctx.at)
    if group:
        since = to_utc_text(ctx.at - GROUP_WINDOW)
        row = conn.execute(
            "SELECT id FROM events WHERE kind = ? AND case_id IS ? AND detail IS ? AND at > ?"
            " ORDER BY at DESC LIMIT 1",
            (kind, ctx.case_id, detail, since),
        ).fetchone()
        if row is not None:
            conn.execute(
                "UPDATE events SET at = ?, count = COALESCE(?, count + 1) WHERE id = ?",
                (at, count, row["id"]),
            )
            return
    conn.execute(
        "INSERT INTO events (at, kind, pincode, scam_type, channel, identifier_type, display,"
        " case_id, detail, count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            at,
            kind,
            ctx.pincode,
            ctx.scam_type,
            ctx.channel,
            ctx.identifier_type,
            ctx.display,
            ctx.case_id,
            detail,
            count or 1,
        ),
    )


def _verdict(case: store.CaseRow | None, verified: bool) -> str:
    if case is None:
        return verdict(CaseFacts(0, 0, 0.0, False), verified=verified)
    facts = CaseFacts(
        case.report_count, case.distinct_reporters, case.weighted_score, case.challenged
    )
    return verdict(facts, verified=verified)


def report_events(
    conn: sqlite3.Connection,
    ctx: Context,
    *,
    status: str,
    before: store.CaseRow | None,
    after: store.CaseRow,
    verified: bool,
) -> None:
    """Events for one accepted report: how it was counted, a burst, a new verdict, new alerts."""
    if status == "counted":
        record(conn, "report", ctx)
    elif status == "merged":
        record(conn, "merged", ctx, group=True)
    suspects = store.suspect_count(conn, after.case_id)
    if suspects:
        record(conn, "burst", ctx, group=True, count=suspects)
    if _verdict(after, verified) == "KNOWN_SCAM" and _verdict(before, verified) != "KNOWN_SCAM":
        record(conn, "known_scam", ctx)
    if ctx.pincode is not None:
        _new_alerts(conn, ctx, ctx.pincode)


def _new_alerts(conn: sqlite3.Connection, ctx: Context, pincode: str) -> None:
    """Announce each alert for the area once a day, when it first appears."""
    events = store.area_events(conn, pincode, to_utc_text(ctx.at - alert_rules.HISTORY))
    for alert in alert_rules.alerts(pincode, events, ctx.at):
        scam_type = alert.get("scam_type")
        seen = conn.execute(
            "SELECT 1 FROM events WHERE kind = 'alert' AND pincode = ? AND detail = ?"
            " AND scam_type IS ? AND at > ?",
            (pincode, alert["type"], scam_type, to_utc_text(ctx.at - timedelta(hours=24))),
        ).fetchone()
        if seen is None:
            where = Context(at=ctx.at, pincode=pincode, scam_type=scam_type)
            record(conn, "alert", where, detail=str(alert["type"]))


def feed(conn: sqlite3.Connection, now: datetime) -> dict[str, list[dict[str, Any]]]:
    """The newest events, and the alerts live right now in every area."""
    rows = conn.execute(
        "SELECT at, kind, pincode, scam_type, channel, identifier_type, display, detail, count"
        " FROM events ORDER BY at DESC, id DESC LIMIT ?",
        (FEED_LIMIT,),
    ).fetchall()
    known = areas()
    events = [
        {
            "at": to_display(str(r["at"])),
            "kind": r["kind"],
            "pincode": r["pincode"],
            "locality": known[r["pincode"]].locality if r["pincode"] in known else None,
            "scam_type": r["scam_type"],
            "channel": r["channel"],
            "identifier_type": r["identifier_type"],
            "display": r["display"],
            "detail": r["detail"],
            "count": int(r["count"]),
        }
        for r in rows
    ]
    live: list[dict[str, Any]] = []
    since = to_utc_text(now - alert_rules.HISTORY)
    for pincode in store.active_areas(conn, to_utc_text(now - alert_rules.WINDOW)):
        for alert in alert_rules.alerts(pincode, store.area_events(conn, pincode, since), now):
            live.append(alert | {"locality": known[pincode].locality if pincode in known else None})
    return {"events": events, "alerts": live}
