"""Migrations: applied in order, once each, on a WAL-mode SQLite database.

Owner: B. Filled in by: B0.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import connect
from app.migrate import MIGRATIONS_DIR, applied_versions, apply_migrations


def _write(directory: Path, name: str, sql: str) -> None:
    (directory / name).write_text(sql, encoding="utf-8")


def test_connect_uses_wal_and_foreign_keys(db_path: Path) -> None:
    conn = connect(db_path)
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_applies_in_order_and_records_versions(db_path: Path, tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    _write(migrations, "0002_b.sql", "ALTER TABLE t ADD COLUMN b TEXT;")
    _write(migrations, "0001_a.sql", "CREATE TABLE t (a TEXT);")
    conn = connect(db_path)
    try:
        assert apply_migrations(conn, migrations) == ["0001_a", "0002_b"]
        columns = [row[1] for row in conn.execute("PRAGMA table_info(t)")]
        assert columns == ["a", "b"]
        assert applied_versions(conn) == ["0001_a", "0002_b"]
    finally:
        conn.close()


def test_second_run_applies_nothing(db_path: Path, tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    _write(migrations, "0001_a.sql", "CREATE TABLE t (a TEXT);")
    conn = connect(db_path)
    try:
        apply_migrations(conn, migrations)
        assert apply_migrations(conn, migrations) == []
    finally:
        conn.close()


def test_failed_migration_is_not_recorded(db_path: Path, tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    _write(migrations, "0001_bad.sql", "CREATE TABLE t (a TEXT); THIS IS NOT SQL;")
    conn = connect(db_path)
    try:
        with pytest.raises(sqlite3.Error):
            apply_migrations(conn, migrations)
        assert applied_versions(conn) == []
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master")]
        assert "t" not in tables
    finally:
        conn.close()


def test_repo_migrations_apply_on_startup(client: TestClient, db_path: Path) -> None:
    expected = sorted(p.stem for p in MIGRATIONS_DIR.glob("*.sql"))
    conn = connect(db_path)
    try:
        assert applied_versions(conn) == expected
    finally:
        conn.close()
