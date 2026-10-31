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

Over HTTPS to Fly.io, network time adds to these; run `perf.py --target https://<api>` after deploying.

## scripts/check.sh, 2026-10-31

Passed end to end: API 406 tests (99% coverage of core and license), judge contract 32/32, held-out simulator all thresholds met, privacy scanners 0 findings, web 180 tests, pip-audit 0 findings in all three projects.
