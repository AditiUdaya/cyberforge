"""Applies api/migrations/*.sql in order and records which ones ran.

Owner: B. Filled in by: B0.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def applied_versions(conn: sqlite3.Connection) -> list[str]:
    _ensure_table(conn)
    rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    return [str(row[0]) for row in rows]


def apply_migrations(conn: sqlite3.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply every migration not yet recorded, each in its own transaction.

    Returns the versions applied by this call. A failing migration is rolled back
    and not recorded, and the error propagates.
    """
    done = set(applied_versions(conn))
    applied: list[str] = []
    for path in sorted(directory.glob("*.sql")):
        version = path.stem
        if version in done:
            continue
        sql = path.read_text(encoding="utf-8")
        try:
            # executescript commits any open transaction first, so BEGIN goes inside the script.
            conn.executescript("BEGIN;\n" + sql)
            conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
            conn.execute("COMMIT")
        except sqlite3.Error:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        applied.append(version)
    return applied


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version TEXT PRIMARY KEY,"
        " applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"
        ")"
    )
