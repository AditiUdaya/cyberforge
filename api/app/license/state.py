"""In-memory verified licence, persisted to license_state, plus the clock high-water mark.

The licence is verified once when it arrives (or at start-up), so the per-request check is
only a time comparison. Expired means locked: nothing here ever deletes data.

Owner: B. Filled in by: B3.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.db import Database
from app.license.verify import InvalidLicence, Licence, verify

# A clock this far behind the latest time seen counts as set back (PRD "Bonus thinking").
ROLLBACK_TOLERANCE = timedelta(minutes=1)
# The high-water mark is written to disk at most this often; a restart loses at most this much.
PERSIST_EVERY = timedelta(minutes=1)


class LicenceState:
    def __init__(self, db: Database, key: Ed25519PublicKey | None) -> None:
        self._db = db
        self._key = key
        self._lock = threading.Lock()
        self._licence: Licence | None = None
        self._high_water: datetime | None = None
        self._persisted: datetime | None = None
        self._load()

    @property
    def licence(self) -> Licence | None:
        return self._licence

    def _load(self) -> None:
        with self._db.read() as conn:
            row = conn.execute(
                "SELECT licence_json, high_water FROM license_state WHERE id = 1"
            ).fetchone()
        if row is None:
            return
        if row["high_water"]:
            self._high_water = self._persisted = datetime.fromisoformat(row["high_water"])
        if row["licence_json"]:
            try:
                self._licence = verify(json.loads(row["licence_json"]), self._key)
            except (InvalidLicence, ValueError):
                self._licence = None

    def effective_now(self, now: datetime) -> datetime:
        """The later of the clock and the high-water mark: setting the clock back gains nothing."""
        return max(now, self._high_water) if self._high_water else now

    def is_valid(self, now: datetime) -> bool:
        """The per-request check. Also advances the high-water mark."""
        with self._lock:
            rolled_back = (
                self._high_water is not None and now < self._high_water - ROLLBACK_TOLERANCE
            )
            self._advance(now)
            if self._licence is None or rolled_back:
                return False
            return self.effective_now(now) < self._licence.expires_at

    def install(self, doc: dict[str, object], now: datetime) -> Licence:
        """Verify and swap in a new licence, then persist it. No restart needed."""
        licence = verify(dict(doc), self._key)
        with self._lock:
            if licence.expires_at <= self.effective_now(now):
                raise InvalidLicence("licence has already expired")
            self._licence = licence
            self._advance(now)
            with self._db.write() as conn:
                conn.execute(
                    "UPDATE license_state SET licence_json = ?, high_water = ? WHERE id = 1",
                    (licence.to_json(), _text(self._high_water)),
                )
            self._persisted = self._high_water
        return licence

    def _advance(self, now: datetime) -> None:
        if self._high_water is None or now > self._high_water:
            self._high_water = now
        if self._persisted is None or self._high_water - self._persisted >= PERSIST_EVERY:
            with self._db.write() as conn:
                conn.execute(
                    "UPDATE license_state SET high_water = ? WHERE id = 1",
                    (_text(self._high_water),),
                )
            self._persisted = self._high_water


def _text(when: datetime | None) -> str | None:
    return when.isoformat() if when else None
