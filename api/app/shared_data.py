"""Reads the shared/ contract files (data, vectors) that both the API and the web app use.

shared/ sits next to api/ in the repo and at /srv/shared in the container; SCAM_MAP_SHARED_DIR
overrides both.

Owner: B. Filled in by: B1.
"""

from __future__ import annotations

import json
import os
from functools import cache
from pathlib import Path
from typing import Any

_DEFAULT = Path(__file__).resolve().parents[2] / "shared"


def shared_dir() -> Path:
    return Path(os.environ.get("SCAM_MAP_SHARED_DIR", str(_DEFAULT)))


@cache
def data_items(name: str) -> tuple[dict[str, Any], ...]:
    """The items list of shared/data/<name>.json, read once."""
    doc = json.loads((shared_dir() / "data" / f"{name}.json").read_text(encoding="utf-8"))
    return tuple(doc["items"])
