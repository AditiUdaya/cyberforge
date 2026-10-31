<!-- Test run log: check.sh passes, verify_deployed.sh runs, stopwatch report times. Owner: A (A6) and B (B9). Filled in by: A6. -->
# Results

Test runs are appended here.

## B8 performance, local, 31 Oct

`judge/perf.py --target local --reports 100000` on a Windows laptop (one uvicorn worker, SQLite WAL):

| What | n | p50 | p95 | max |
| --- | --- | --- | --- | --- |
| Load | 100,000 reports in 264 s (379/s), 0 refused | | | |
| Lookup | 2,000 | 1.9 ms | 2.6 ms | 5.2 ms |
| Report | 500 | 3.5 ms | 5.2 ms | 38.3 ms |
| Map (5 km, 7 days) | 100 | 10.9 ms | 31.3 ms | 40.6 ms |

Over a network, round-trip time adds to these; `perf.py --target <url>` measures any address.

## scripts/check.sh, 2026-10-31

Passed end to end: API 406 tests (99% coverage of core and license), judge contract 32/32, held-out simulator all thresholds met, privacy scanners 0 findings, web 180 tests, pip-audit 0 findings in all three projects.

## verify_deployed.sh, 2026-10-31T17:07Z, https://scam-map-api-shubhang.fly.dev

- PASS  health
- PASS  licence valid
- PASS  lookup under 500 ms
- PASS  contract
- PASS  simulator (held-out seeds)
- FAIL  metamorphic (tuning seeds)

Notes on that run against https://scam-map-api-shubhang.fly.dev (Fly.io, Singapore):

- Simulator held-out: every family met its threshold. R2 was 49/50: one scenario (R2:120) failed only because a
  request got no reply within 30 s (client `ReadTimeout`), not on any rule.
- Metamorphic: the run stopped on a second 30 s network timeout. `metamorphic.py` now records a network error as one
  failed check instead of stopping (fixed after this run).
- Fly restarted the machine once during the run (`requested_stop=true`, not out of memory). A restart measured on
  purpose afterwards took about 4 s from stop to the first `200`, so the 30 s stalls were the network path from
  Bengaluru to Singapore, not the server.
- After redeploying: contract 32/32 against the live address, licence intact.
