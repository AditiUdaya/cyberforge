"""Shared fixtures: in-process app, temporary database, injectable clock.

Owner: B. Filled in by: B0.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.clock import FixedClock
from app.main import create_app

START = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(START)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.sqlite"


@pytest.fixture
def app(db_path: Path, clock: FixedClock) -> FastAPI:
    return create_app(db_path=db_path, clock=clock)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
