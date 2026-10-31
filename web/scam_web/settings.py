"""Where the API and the shared contract files are.

Owner: A. Filled in by: A0.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_API_URL = "http://127.0.0.1:8000"
_REPO_SHARED = Path(__file__).resolve().parents[2] / "shared"


def api_url() -> str:
    return os.environ.get("SCAM_MAP_API_URL", DEFAULT_API_URL).rstrip("/")


def shared_dir() -> Path:
    return Path(os.environ.get("SCAM_MAP_SHARED_DIR", str(_REPO_SHARED)))
