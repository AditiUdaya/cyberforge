<!-- Demo runbook and PRD scoring map. Owner: A and B. -->
# Demo runbook

Everything the team and the judges need to run and check the demo, in order. Hosting is a laptop on the judges'
Wi-Fi (DECISIONS D59, D62).

## 1. Before the demo

| Step | Command or action |
| --- | --- |
| Start everything | `scripts/run_local.sh` (prints the Wi-Fi address; `--fresh` resets to demo data) |
| Open the firewall once | the administrator command in [infra/README.md](../infra/README.md) |
| Check from a second device | `curl http://<address>:8000/health` returns `{"ok":true}` |
| Keep the laptop awake | plugged in, sleep off |
| Long licence | `.local/demo/licence-long.json` (valid for a year; make another with `license_sign.py --expires-in 365d`) |

## 2. The licence demo (PRD row 5, four steps, no restart)

**Sign the 5-minute file about a minute before step 2.** A licence's `expires_at` is an absolute time, so a file signed
earlier is already expired and is refused.

```bash
uv run --project api python scripts/license_sign.py --licensee "Demo Bank" --expires-in 5m --out .local/demo/licence-5min.json
```

| Step | Do | Expect |
| --- | --- | --- |
| 1 | `curl http://<address>:8000/license`, then look up a number that has reports | licensee and expiry shown; lookup `200` |
| 2 | `curl -X POST -H "content-type: application/json" --data-binary @.local/demo/licence-5min.json http://<address>:8000/license` | `200`; the app keeps working |
| 3 | Wait 5 minutes, then look up the same number | `403 {"error": "LICENSE_EXPIRED"}`; `/health` and `/license` still answer; the website shows "Licence expired. Contact your provider." |
| 4 | Upload `.local/demo/licence-long.json` the same way | `200`; the same lookup returns the same answer as in step 1: nothing was lost |

The whole sequence as one script (it waits for expiry itself):

```bash
DEMO_NUMBER=08189485574 scripts/license_demo.sh http://<address>:8000 .local/demo/licence-5min.json .local/demo/licence-long.json
```

On the website the same upload is on the Licence screen. The file picker opens in your last folder: type the full
path into its filename box if `.local` is hidden.

## 3. Three-minute story for the video and the pitch

| Time | Show | Say |
| --- | --- | --- |
| 0:00 | Check: paste the PRD's example message | one card per identifier, masked until 3 people, "Reported by N people near you" |
| 0:30 | Report: under 20 seconds, icons only | no login, anonymous, any language |
| 1:00 | Map and the live panel while someone reports | alerts only for unusual activity; fakes never alert |
| 1:30 | Fake reports: the 40-friends dataset (`scripts/curl_load.sh`) | they count as one reporter; the bakery is not labelled a scam |
| 2:00 | Dispute a number | one dispute per number; caps the verdict at Suspicious |
| 2:15 | The four licence steps | expiry locks, never deletes; renewed without a restart |
| 2:50 | Privacy | nothing logged; HMAC and fingerprints only |

## 4. What the PRD scores and where we stand

| PRD row | Points | How the app meets it | Evidence | Measured by our tools |
| --- | --- | --- | --- | --- |
| 1 Stops fake reports | 20 | one reporter, one network, copied notes, bursts and rate limits each count once or little | 15 simulator families; 750/750 held-out; fresh seeds at 75, 300 and 900 scenarios all pass | yes |
| 2 Lookup gives the right answer | 15 | normalised matching, verdict from independent groups, masked until 3, lookup under 5 ms locally | datasets 121/121; perf in [RESULTS.md](RESULTS.md) | yes |
| 3 Map and alerts | 10 | spike and new-type alerts from counted reports only; 30-day limit | map and alert families and datasets | yes |
| 4 Privacy | 15 | keyed HMACs, note fingerprints, no request logs, "reported" wording | five scanners, 0 findings | yes |
| 5 Server and licence | 15 | signed licence checked on every request, hot-swap, lock not delete; reachable on the Wi-Fi | licence tests; live four-step demo | partly (no HTTPS) |
| 6 Usability | 15 | icon-first mobile screens, English and Hindi | stopwatch test with three new users | no, judged by people |
| 7 Demo and pitch | 10 | the story above | video, pitch | no, judged by people |
| Bonus | 7 | verified numbers 3, disputes 2, fakes never alert 2 | contract and dataset checks | yes |

Our tools score **82.0 of 82** on the rows they can measure; the PRD total is 100 plus 7 bonus, 107. Rows 6 and 7
(25 points) and the HTTPS part of row 5 are the open items.

## 5. Questions to expect

| Question | Short answer |
| --- | --- |
| Can someone brand a number a scam with fake reports? | Not with the four tricks: a known scam needs 3 independent groups and a score of 3.0; bursts are capped as one group. |
| What does "verified business" mean? | On the organisers' Appendix C list. We do not check identity. |
| Where is personal data kept? | Nowhere readable: reporters, networks and identifiers are keyed hashes; notes are fingerprints; there are no request logs. |
| Why http? | The server is a laptop on the judges' Wi-Fi. Public HTTPS is future scope. |
| Can the licence be cheated? | The date is signed, the key is offline, and a clock set back counts as expired. |
