"""FastAPI dependencies: the shared database, clock and HMAC keyring held on app.state.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

from typing import cast

from fastapi import Request

from app.clock import Clock
from app.core.identity import Keyring
from app.db import Database


def get_db(request: Request) -> Database:
    return cast(Database, request.app.state.db)


def get_clock(request: Request) -> Clock:
    return cast(Clock, request.app.state.clock)


def get_keyring(request: Request) -> Keyring:
    return cast(Keyring, request.app.state.keyring)
