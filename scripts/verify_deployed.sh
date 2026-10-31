#!/usr/bin/env bash
# Full test run against the HTTPS address: scripts/verify_deployed.sh https://<host> --yes
# Resets the server first (contract, simulator and metamorphic runs all call /admin/reset),
# so never run it after the judges have loaded their data. Appends a summary to docs/RESULTS.md.
# Owner: A. Filled in by: A0 (health), A6 (every layer).
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=${1:-}
if [ -z "$BASE" ] || [ "${2:-}" != "--yes" ]; then
  echo "usage: $0 https://<host> --yes" >&2
  echo "This RESETS the server: every stored report is deleted." >&2
  exit 2
fi
BASE=${BASE%/}
case "$BASE" in https://*) ;; *) echo "warning: $BASE is not HTTPS; the PRD requires HTTPS" >&2 ;; esac

results=()
run() {
  local name=$1; shift
  echo "== $name"
  if "$@"; then results+=("PASS  $name"); else results+=("FAIL  $name"); fi
}

health() {
  local body code
  body=$(curl -s -w ' %{http_code}' "$BASE/health")
  code=${body##* }
  echo "${body% *}"
  [ "$code" = 200 ] && [ "${body% *}" = '{"ok":true}' ]
}

licence() {
  local body
  body=$(curl -s "$BASE/license")
  echo "$body"
  case "$body" in *'"valid":true'*) return 0 ;; *) echo "licence is not valid: upload one first" >&2; return 1 ;; esac
}

latency() {
  local worst=0 t ms
  for _ in $(seq 1 20); do
    t=$(curl -s -o /dev/null -w '%{time_total}' "$BASE/lookup?type=phone&value=%2B919876543210")
    ms=$(awk -v t="$t" 'BEGIN { printf "%d", t * 1000 }')
    [ "$ms" -gt "$worst" ] && worst=$ms
  done
  echo "slowest of 20 lookups: ${worst} ms"
  [ "$worst" -lt 500 ]
}

run "health" health
run "licence valid" licence
run "lookup under 500 ms" latency
run "contract" bash -c "cd judge && uv run python contract.py --target '$BASE'"
run "simulator (held-out seeds)" bash -c "cd judge && uv run python runner.py --seeds holdout --target '$BASE' --fail-under-thresholds"
run "metamorphic (tuning seeds)" bash -c "cd judge && uv run python metamorphic.py --seeds tuning --target '$BASE'"

stamp=$(date -u +%Y-%m-%dT%H:%MZ)
{
  echo
  echo "## verify_deployed.sh, $stamp, $BASE"
  echo
  for r in "${results[@]}"; do echo "- $r"; done
} >> docs/RESULTS.md

echo
printf '%s\n' "${results[@]}"
for r in "${results[@]}"; do case "$r" in FAIL*) exit 1 ;; esac; done
echo "verify_deployed passed"
