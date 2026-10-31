<!-- How to run and explain the Community Scam Map (judged, PRD row 7). Owner: A and B. Filled in by: A7 (run steps) and B9 (trust rules, licence). -->
# Community Scam Map

People warn each other about scam phone numbers, UPI IDs, links and SMS senders, and check one before they
trust it. Anyone can report in under a minute, with no login. A lookup answers in milliseconds with one of
**Known scam**, **Suspicious**, **No reports** or **Verified business**, worded as "Reported by N people near
you". A map shows the last 7 days by area, and alerts fire only when something is unusual.

The hard part is fake reports. The trust rules below stop all four tricks in the brief (40 friends, 22 accounts
on one Wi-Fi, one person six times, junk) without missing real scams, and a judge simulator proves it on data
the rules were never tuned on.

| | |
| --- | --- |
| API (judged address) | `https://<api>.fly.dev` (Fly.io, always on, HTTPS) |
| Mobile website | `https://<web>.fly.dev` (Streamlit, English and Hindi, works with icons alone) |
| Brief | [docs/PRD.pdf](docs/PRD.pdf), our plan in [docs/SPEC.md](docs/SPEC.md), design in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |

## Run it

You need [uv](https://docs.astral.sh/uv/) (Python 3.12 is installed by uv if missing) and Git. Full setup,
including Windows notes, is in [docs/SETUP.md](docs/SETUP.md).

```bash
git clone <repo-url> scam-map && cd scam-map
```

**1. Start the API** on port 8000. It needs an HMAC key (any long random string locally):

```bash
cd api && uv sync --frozen && SCAM_MAP_HMAC_KEY=change-me-to-a-long-random-string uv run uvicorn app.main:app
```

`GET http://127.0.0.1:8000/health` returns `{"ok": true}`. Every other route answers
`403 {"error": "LICENSE_EXPIRED"}` until a licence is loaded.

**2. Load a licence.** Make a key pair once (the private key goes to `~/.scam-map/license.key`, never the repo),
sign a licence and upload it:

```bash
uv run --project api python scripts/license_keygen.py
```

```bash
uv run --project api python scripts/license_sign.py --licensee "Demo Bank" --expires-in 30d --out licence.json
```

```bash
curl -X POST -H "content-type: application/json" --data-binary @licence.json http://127.0.0.1:8000/license
```

**3. Start the website** on port 8501, in another terminal:

```bash
cd web && uv sync --frozen && SCAM_MAP_API_URL=http://127.0.0.1:8000 uv run streamlit run app.py
```

Open http://127.0.0.1:8501 on a phone-sized window. Try the PRD's example message on the Check screen:
`Your KYC has expired. Update at http://www.sbi-kyc.in/pay?utm=sms or call +91 98765 43210`.

**4. Run the judge simulator** against a server it starts itself:

```bash
cd judge && uv sync --frozen && uv run python runner.py --seeds holdout --target local
```

Deploying to Fly.io is step by step in [infra/README.md](infra/README.md).

## How trust rules work

Every report about the same identifier (after normalising, so `+91 98765 43210`, `09876543210`, `98765-43210`
and `919876543210` are one number) forms a case. Each time a report arrives, the rules re-read the whole case.
All numbers are in [api/app/core/trust_config.py](api/app/core/trust_config.py).

1. **One person is one person.** Reports with the same `reporter_id` count once, however far apart.
2. **One connection is one person.** Reports from the same `ip_prefix` within 24 hours merge into one. That
   stops 22 accounts on one Wi-Fi.
3. **Copy-paste is one voice.** Notes that are 80% or more alike (character shingles, so English, Hindi and
   Hinglish all work) merge across different people.
4. **Too many too fast is slowed down.** More than 3 reports from one reporter within an hour get `429`.
5. **Coordinated bursts are capped.** When 5 or more brand-new reporters hit one identifier within an hour,
   and either most of their notes are empty or copied, or all their incidents happened within 15 minutes, the
   whole group counts as **one** reporter and adds at most **1.5** to the score. That stops the 40 friends.
   A real sudden wave, where people were called at different times and write their own words, is not capped.
6. **Own words count more.** Each independent group weighs 1.0 with a note of at least 15 characters, 0.6
   without.
7. **Verdict.** On the verified list (PRD Appendix C): always **Verified business**. Otherwise **Known scam**
   needs at least **3 independent groups** and a score of at least **3.0**, and is capped at **Suspicious** while
   a business disputes the number. Any accepted report short of that is **Suspicious**; none is **No reports**.
8. **Fakes never alert.** Each report is marked `counted`, `merged` or `suspect`. The map and alerts use
   only `counted` reports, so fakes the rules ignored never move a map point or set off an alert.

`distinct_reporters` in a lookup is the number of independent groups, so the 40 friends show as 1 and the
bakery's number stays masked.

**Why a bombed bakery is not labelled a scam:** whichever way the 40 friends send their reports (one Wi-Fi or 40,
copied, lightly edited or empty notes), they arrive as a burst of new reporters telling one story about one
moment. They count as one reporter, weighing at most 1.5, and stay below both bars for Known scam.

**What these rules cannot do:** tell 40 friends who each write their own words, on different days, from
different networks, apart from a real campaign. That attack costs real effort for every report, and the bakery
can dispute the number, which caps it at Suspicious while under review.

## How the licence works

A licence is a small signed file:

```json
{"licensee": "Demo Bank", "expires_at": "2026-11-15T10:05:00+05:30", "signature": "..."}
```

- **Signed offline.** The signature is Ed25519 over the canonical JSON of `licensee` and `expires_at` (sorted
  keys, no spaces). The private key stays on our laptop (`~/.scam-map/license.key`, blocked by `.gitignore`);
  the server holds only the public key, built into the image. Editing the date breaks the signature.
- **Checked on every request.** The verified licence sits in memory, so the check is one time comparison.
  When it has expired, every route except `/health` and `/license` answers exactly
  `403 {"error": "LICENSE_EXPIRED"}`, and the app shows "Licence expired. Contact your provider."
- **Renewed without a restart.** `POST /license` verifies the new file, swaps it in memory and saves it on the
  volume, so it survives restarts. A refused file leaves the current licence in force.
- **Expired locks, never deletes.** Data is untouched; renewing brings it all back. Reset keeps the licence too.
- **Setting the clock back does not help.** The server remembers the latest time it has seen (saved to disk).
  A clock more than a minute behind it counts as expired, and expiry is judged against the later of the two.

The PRD's four-step demo, end to end against any server (waits for the short licence to expire):

```bash
scripts/license_demo.sh https://<api>.fly.dev licence-5min.json licence-long.json
```

## Privacy

| PRD rule | How |
| --- | --- |
| Reporters anonymous | No login, name or phone number. `reporter_id`, `ip_prefix` and identifiers are stored only as keyed HMACs; notes only as keyed MinHash fingerprints that cannot be turned back into text. Area only, never a location. The website sends a random id per browser session. |
| Hidden until 3 people | `display_value` is masked (`98XXXXX210`, `r***@okaxis`, `sbi***.in/...`, `HD****`) until 3 independent reporters. |
| "Reported", not "scammer" | "Reported by N people near you" in both languages; a scanner fails the build on banned words. |
| No scraping | The API makes no outbound calls at all. |
| No personal data in logs | Access logs are off; a scanner reads every log line of a full run. |

The privacy scanners (`cd judge && uv run python -m scanners.all --target local`) run the simulator and then
check every reply, every server log line and the raw database bytes for anything a reporter sent.

## Tests

| Layer | What | Command | Result (31 Oct) |
| --- | --- | --- | --- |
| Unit and property | Normaliser, masking, verdicts, trust rules, licence; Hypothesis with 1,000 examples per property | `cd api && uv run pytest` | 400+ tests, 98% coverage of `core/` and `license/` |
| Contract | Every PRD route, status and reply schema | `cd judge && uv run python contract.py --target local` | 32/32 |
| Judge simulator | 15 scenario families, tuned on seeds 1 to 10, reported on held-out seeds 101 to 150 | `uv run python runner.py --seeds holdout --target local` | 750/750 scenarios, all thresholds met |
| Metamorphic | Same scenario shuffled, re-spelled, other time offsets, junk mixed in | `uv run python metamorphic.py --seeds holdout --target local` | 1,600/1,600 identical |
| Privacy scanners | Replies, logs, database, wording, hardcoding | `uv run python -m scanners.all --target local` | 0 findings |
| Robustness | Fuzzed bodies and queries, 50 concurrent reports | in the API tests | no 5xx, exact counts |
| Performance | 100k reports, 2,000 lookups, 500 reports | `uv run python perf.py --target <url>` | see [docs/RESULTS.md](docs/RESULTS.md) |
| UI | Every screen in English, Hindi and icon-only mode | `cd web && uv run pytest` | 180 tests |

`scripts/check.sh` runs all local layers; `scripts/verify_deployed.sh https://<api> --yes` runs them against the
deployed server (it resets it first).

## Layout

```text
api/      FastAPI server: routes, core rules, licence, migrations, tests      (Person B)
web/      Streamlit mobile website: six screens, English and Hindi, icons      (Person A)
judge/    Contract tests, judge simulator, metamorphic tests, scanners, perf   (Person B)
shared/   The contract: JSON Schemas, PRD data (areas, verified, scam types), test vectors
infra/    Dockerfiles and Fly.io config                                        (Person A)
scripts/  check.sh, verify_deployed.sh, licence key, sign and demo scripts
docs/     PRD, spec, architecture, decisions, results, setup
```

## Known limits

- **40 friends writing their own words over days** cannot be told apart from a real campaign (see above).
- **Device id per session.** The website's anonymous id lasts one browser session (DECISIONS D57); a returning
  visitor on another network counts as a new reporter.
- **One API machine.** SQLite on one volume means one machine; fine for this load (see performance), but scaling
  out would mean moving to Postgres.
