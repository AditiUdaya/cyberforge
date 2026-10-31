"""SQLite connection in WAL mode on the persistent volume; one place that opens the database.

Owner: B. Filled in by: B0.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("scam_map.sqlite")


def db_path_from_env() -> Path:
    return Path(os.environ.get("SCAM_MAP_DB_PATH", str(DEFAULT_DB_PATH)))


def connect(path: Path) -> sqlite3.Connection:
    """Open the database in autocommit mode; callers open transactions explicitly."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn
