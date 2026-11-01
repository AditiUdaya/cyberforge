#!/usr/bin/env bash
# Runs the four PRD licence demo steps against a server with no restart.
#   scripts/license_demo.sh http://<address>:8000 licence-5min.json licence-long.json
# Step 3 waits for the short licence to expire (5 minutes for the real demo).
# It only reads data: the lookup before expiry must equal the lookup after renewal.
# DEMO_NUMBER=<a number that has reports> makes "the old data is still there" mean something;
# without it the script looks up +919876543210, which only has reports in the PRD's own data.
# The short licence's expires_at is an absolute time: sign it just before running this.
# Owner: B. Filled in by: B3.
set -euo pipefail

if [ $# -ne 3 ]; then
  echo "usage: $0 BASE_URL SHORT_LICENCE.json LONG_LICENCE.json" >&2
  exit 2
fi
BASE=${1%/}
SHORT=$2
LONG=$3
NUMBER=${DEMO_NUMBER:-+919876543210}
WAIT_LIMIT=${DEMO_WAIT_LIMIT:-420}

probe() { curl -s -G "$BASE/lookup" --data-urlencode "type=phone" --data-urlencode "value=$NUMBER" "$@"; }
status() { probe -o /dev/null -w '%{http_code}'; }
fail() { echo "FAIL: $*" >&2; exit 1; }

echo "== 1. The app works, and GET /license shows who and until when"
curl -s "$BASE/license"; echo
[ "$(status)" = 200 ] || fail "lookup is not 200 before the demo; upload a long licence first"
before=$(probe)
echo "lookup of $NUMBER: $before"

echo "== 2. Upload the licence that expires soon"
reply=$(curl -s -w ' %{http_code}' -X POST -H 'content-type: application/json' --data-binary "@$SHORT" "$BASE/license")
echo "$reply"
[ "${reply##* }" = 200 ] || fail "short licence was refused (is it already expired? sign it just before)"

echo "== 3. Wait for it to expire; lookups must then be 403 LICENSE_EXPIRED"
start=$(date +%s)
while :; do
  code=$(status)
  [ "$code" = 403 ] && break
  [ $(( $(date +%s) - start )) -gt "$WAIT_LIMIT" ] && fail "still $code after ${WAIT_LIMIT}s"
  sleep 5
done
echo "after $(( $(date +%s) - start ))s: $(probe)"
[ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health")" = 200 ] || fail "/health must keep working when expired"
echo "/health still 200; GET /license: $(curl -s "$BASE/license")"

echo "== 4. Upload the long licence; the app works again with the old data"
reply=$(curl -s -w ' %{http_code}' -X POST -H 'content-type: application/json' --data-binary "@$LONG" "$BASE/license")
echo "$reply"
[ "${reply##* }" = 200 ] || fail "long licence was refused"
start=$(date +%s)
until [ "$(status)" = 200 ]; do
  [ $(( $(date +%s) - start )) -gt 60 ] && fail "not working again within a minute"
  sleep 1
done
after=$(probe)
echo "lookup of $NUMBER: $after"
[ "$before" = "$after" ] || fail "data changed across expiry and renewal"

echo "PASS: all four licence demo steps, no restart"
