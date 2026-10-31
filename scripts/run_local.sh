#!/usr/bin/env bash
# Runs the whole app on this laptop: API on :8000, website on :8501, a licence signed with your
# key, and demo data. Ctrl+C stops both. Data lives in .local/ (gitignored) and survives restarts.
#   scripts/run_local.sh            start, load demo data, open http://127.0.0.1:8501
#   scripts/run_local.sh --keep     start with the data already in .local/ (no reset, no demo data)
# Judging still needs the cloud deployment (PRD row 5); this is for building and rehearsing.
# Owner: A. Filled in by: A6.
set -euo pipefail
cd "$(dirname "$0")/.."

API_PORT=8000
WEB_PORT=8501
LOCAL=.local
KEY="$HOME/.scam-map/license.key"
mkdir -p "$LOCAL"

if [ ! -f "$KEY" ]; then
  echo "No licence key at $KEY. Make one first:" >&2
  echo "  uv run --project api python scripts/license_keygen.py" >&2
  exit 1
fi

venv_python() {
  if [ -x "$1/.venv/Scripts/python.exe" ]; then echo "$1/.venv/Scripts/python.exe"; else echo "$1/.venv/bin/python"; fi
}

echo "== Installing locked dependencies"
(cd api && uv sync --frozen --quiet)
(cd web && uv sync --frozen --quiet)
(cd judge && uv sync --frozen --quiet)

# One HMAC key for this laptop, kept so stored reports stay reachable between runs.
if [ ! -f "$LOCAL/hmac.key" ]; then
  uv run --project api python -c "import secrets; print(secrets.token_hex(32))" > "$LOCAL/hmac.key"
fi

API_PID=""
cleanup() {
  if [ -n "$API_PID" ]; then kill "$API_PID" 2>/dev/null || true; wait "$API_PID" 2>/dev/null || true; fi
  echo "stopped"
}
trap cleanup EXIT INT TERM

echo "== Starting the API on http://127.0.0.1:$API_PORT"
(cd api && SCAM_MAP_DB_PATH="../$LOCAL/scam_map.sqlite" SCAM_MAP_HMAC_KEY="$(cat "../$LOCAL/hmac.key")" \
  exec "$(venv_python .)" -m uvicorn app.main:app --port "$API_PORT" --no-access-log --log-level warning) &
API_PID=$!
for _ in $(seq 1 60); do
  curl -sf "http://127.0.0.1:$API_PORT/health" >/dev/null && break
  sleep 0.5
done
curl -sf "http://127.0.0.1:$API_PORT/health" >/dev/null || { echo "API did not start" >&2; exit 1; }

echo "== Loading a 30-day licence signed with your key"
uv run --project api python scripts/license_sign.py --licensee "Local demo" --expires-in 30d \
  --out "$LOCAL/licence-local.json" >/dev/null
curl -s -X POST -H 'content-type: application/json' --data-binary "@$LOCAL/licence-local.json" \
  "http://127.0.0.1:$API_PORT/license"
echo

if [ "${1:-}" != "--keep" ]; then
  echo "== Loading demo data (resets the local database)"
  (cd judge && uv run python seed_demo.py --target "http://127.0.0.1:$API_PORT")
fi

echo
echo "== Website: http://127.0.0.1:$WEB_PORT   (Ctrl+C stops everything)"
cd web
SCAM_MAP_API_URL="http://127.0.0.1:$API_PORT" "$(venv_python .)" -m streamlit run app.py \
  --server.port "$WEB_PORT" --server.headless true
