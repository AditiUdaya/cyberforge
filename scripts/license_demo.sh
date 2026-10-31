#!/usr/bin/env bash
# Runs the four PRD licence demo steps against a server with no restart.
#   scripts/license_demo.sh https://<host> licence-5min.json licence-long.json
# Step 3 waits for the short licence to expire (5 minutes for the real demo).
# It only reads data: the lookup before expiry must equal the lookup after renewal.
# Owner: B. Filled in by: B3.
set -euo pipefail

if [ $# -ne 3 ]; then
  echo "usage: $0 BASE_URL SHORT_LICENCE.json LONG_LICENCE.json" >&2
  exit 2
fi
BASE=${1%/}
SHORT=$2
LONG=$3
PROBE="$BASE/lookup?type=phone&value=%2B919876543210"
WAIT_LIMIT=${DEMO_WAIT_LIMIT:-420}

status() { curl -s -o /dev/null -w '%{http_code}' "$1"; }
fail() { echo "FAIL: $*" >&2; exit 1; }

echo "== 1. The app works, and GET /license shows who and until when"
curl -s "$BASE/license"; echo
[ "$(status "$PROBE")" = 200 ] || fail "lookup is not 200 before the demo; upload a long licence first"
before=$(curl -s "$PROBE")
echo "lookup: $before"

echo "== 2. Upload the licence that expires soon"
reply=$(curl -s -w ' %{http_code}' -X POST -H 'content-type: application/json' --data-binary "@$SHORT" "$BASE/license")
echo "$reply"
[ "${reply##* }" = 200 ] || fail "short licence was refused"

echo "== 3. Wait for it to expire; lookups must then be 403 LICENSE_EXPIRED"
start=$(date +%s)
while :; do
  code=$(status "$PROBE")
  [ "$code" = 403 ] && break
  [ $(( $(date +%s) - start )) -gt "$WAIT_LIMIT" ] && fail "still $code after ${WAIT_LIMIT}s"
  sleep 5
done
echo "after $(( $(date +%s) - start ))s: $(curl -s "$PROBE")"
[ "$(status "$BASE/health")" = 200 ] || fail "/health must keep working when expired"
echo "/health still 200; GET /license: $(curl -s "$BASE/license")"

echo "== 4. Upload the long licence; the app works again with the old data"
reply=$(curl -s -w ' %{http_code}' -X POST -H 'content-type: application/json' --data-binary "@$LONG" "$BASE/license")
echo "$reply"
[ "${reply##* }" = 200 ] || fail "long licence was refused"
start=$(date +%s)
until [ "$(status "$PROBE")" = 200 ]; do
  [ $(( $(date +%s) - start )) -gt 60 ] && fail "not working again within a minute"
  sleep 1
done
after=$(curl -s "$PROBE")
echo "lookup: $after"
[ "$before" = "$after" ] || fail "data changed across expiry and renewal"

echo "PASS: all four licence demo steps, no restart"
