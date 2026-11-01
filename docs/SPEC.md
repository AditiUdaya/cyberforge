# Community Scam Map: Build Spec

Oct 31, 2026 · Shubhang

> **Status, 1 Nov:** this is the original plan. Four decisions changed it, all in [DECISIONS.md](DECISIONS.md): the web app is Streamlit, not React and Playwright (D54, D55); hosting is a laptop on the judges' Wi-Fi, not a cloud host (D59, D62); the live activity panel was added (D60); disputes are limited to one per number (D61). Where this file mentions React, Vite, Playwright or a cloud host, read those decisions instead.

Two people build the scam map in parallel, each driving Claude Code one numbered task at a time. The organisers' brief, `docs/PRD.pdf`, is the source of truth; `docs/ARCHITECTURE.md` says how we meet it and `docs/DECISIONS.md` records why. Where anything here conflicts with the PRD, the PRD wins.

## What we are scored on

| PRD row | Points | What must be true | Owner |
| --- | --- | --- | --- |
| 1 Stops fake reports | 20 | None of the four tricks makes a number `KNOWN_SCAM` | B |
| 2 Lookup gives the right answer | 15 | Real scams `KNOWN_SCAM`, unreported `NO_REPORTS`, all formats match, under 0.5 s | B |
| 3 Map and alerts | 10 | Spike alerts, normal areas quiet, new types alert, month-old reports off the map | B |
| 4 Privacy | 15 | Masked under 3 reporters, anonymous, careful wording; failure disqualifies | Both |
| 5 Server and licence | 15 | Four-step licence demo live on HTTPS with no restart | B server, A deploy |
| 6 Easy to report | 15 | Under 60 s on a phone, usable in Hindi or with icons, no login | A |
| 7 Demo and code | 10 | Runs from the README, clear trust and licence explanation, clear pitch | Both |
| Bonus | 7 | Verified numbers 3, disputes 2, fakes never alert 2 | B |

Automatic disqualification: a reporter can be identified, exact locations stored, personal data scraped, or code written before the event.

## Work split

Person A owns the web app, deployment and UI testing. Person B owns the API, trust rules, licence and the judge simulator. Each person edits only their own folders; `shared/` changes need the other person's OK.

| Workstream | Owner | Folder |
| --- | --- | --- |
| Screens: Check, Report, Map, Challenge, Licence, How it works | A | `web/src/pages` |
| English and Hindi dictionaries, icons | A | `web/src/i18n`, `web/src/icons` |
| Message extractor (pasted text to identifiers) | A | `web/src/extract` |
| Browser tests (Playwright, mobile) | A | `web/e2e` |
| Cloud host, HTTPS, volume, secrets, deploy script | A | `infra/` |
| Deployed verification script | A | `scripts/verify_deployed.sh` |
| PRD routes and schemas | B | `api/app/routes` |
| Normaliser, validation, trust rules, verdicts, masking, map, alerts | B | `api/app/core` |
| Licence gate, verification, state | B | `api/app/license` |
| Licence key and signing tools (offline) | B | `scripts/license_*.py` |
| Judge simulator, scenario families, scorecard, scanners | B | `judge/` |
| Contract schemas, data files, test vectors | B drafts, A reviews | `shared/` |
| Check script | B drafts, A reviews | `scripts/check.sh` |

## Repo layout

```text
scam-map/
  CLAUDE.md                  rules Claude Code reads first
  README.md                  how to run, how trust rules work, how the licence works (judged)
  docs/
    PRD.pdf                  organisers' brief: the source of truth
    SPEC.md  ARCHITECTURE.md  DECISIONS.md  RESULTS.md
  shared/
    contract/                JSON Schemas for every PRD route, request and reply
    data/                    areas.json (Appendix B + datameet extras), verified.json (Appendix C),
                             scam_types.json, channels.json
    vectors/                 normalise.json, mask.json, extract.json
  api/                       Person B: FastAPI, Python 3.12, uv, ruff, mypy, SQLite
    app/routes/  app/core/  app/license/  app/db.py  app/clock.py
    migrations/
    tests/                   unit, property, licence, in-process contract
  judge/                     Person B: black-box tests and the judge simulator
    families/                one module per scenario family
    generator.py             seeded scenario generator
    runner.py                posts scenarios to a base URL or the in-process app
    scorecard.py             scores a run against the PRD rubric
    contract.py              black-box contract tests
    scanners/                responses, logs, database, wording, hardcoding
    perf.py                  latency over HTTPS
    seeds.toml               tuning seeds and held-out seeds
  web/                       Person A: Streamlit, Python 3.12, uv, ruff, mypy (DECISIONS D54)
    app.py  pages/  i18n/  icons/  extract/  api_client.py
    tests/                   Streamlit AppTest UI tests
  infra/                     API and web Dockerfiles, host config (two services, D55)
  scripts/
    check.sh                 local zero-warning gate
    verify_deployed.sh       full test run against the HTTPS address
    license_keygen.py  license_sign.py  license_demo.sh
```

`.gitignore` blocks `*.key`, `*.pem` except `api/app/license/public_key.pem`, `.env` and the SQLite file.

## Contracts

Frozen at sync point 1; a later change is one pull request that updates the schema, both sides and the tests together.

| Contract | Where | Rule |
| --- | --- | --- |
| PRD routes | `shared/contract/*.schema.json` | One schema per request and reply, copied field by field from PRD Appendix A. Extra reply fields allowed; required fields and types never change. |
| Errors | All non-2xx replies | `{"error": "..."}`; expired licence is exactly `403 {"error": "LICENSE_EXPIRED"}` |
| Normalisation | `shared/vectors/normalise.json` | Every PRD example, plus at least 60 of our own including junk; Python and the web extractor both pass every case |
| Masking | `shared/vectors/mask.json` | `98XXXXX210`, `r***@okaxis`, `sbi***.in/...`, `HD****` for 0 to 2 reporters; full value at 3 |
| Areas, verified numbers, scam types, channels | `shared/data/*.json` | Copied from PRD Appendix B and C; both sides read these files, nobody retypes them |
| Time | Every `occurred_at` | ISO 8601 with an offset; windows compare instants, so `+05:30`, `Z` and `-05:00` give the same answer |

## Tasks

Each task is one Claude Code session on one branch. Hours count from the start; "Needs" lists tasks merged first. Done means the "Done when" tests pass and `scripts/check.sh` is clean.

**Person B: API, trust rules, licence, judge simulator**

| ID | Hours | Task | Needs | Done when |
| --- | --- | --- | --- | --- |
| B0 | 0 to 1 | FastAPI app with `GET /health` returning `{"ok": true}`, injectable clock, SQLite with migrations, Dockerfile, `check.sh`, `CLAUDE.md` | none | The container runs locally and `/health` returns `{"ok": true}` |
| B1 | 1 to 3 | `shared/contract` schemas for all nine routes; `shared/data` from Appendix B and C; `shared/vectors` from every PRD example plus our own; stub routes returning schema-valid replies; `judge/contract.py` black-box tests | B0 | Contract tests pass in-process and against the deployed stub |
| B2 | 3 to 5 | Normaliser and validation (`400` rules), verified list, `POST /reports` storing HMACs only, `GET /lookup` with verdict, masking and evidence, `POST /admin/reset` | B1 | All vectors pass; property tests (below) pass; unreported is `200 NO_REPORTS`, `12345` is `400` |
| B3 | 5 to 7 | Licence: keygen and signing scripts, verification, gate on every request, `GET /license`, `POST /license` hot swap with persistence, clock high-water mark, `scripts/license_demo.sh` | B2 | Licence test suite (below) passes; the demo script runs all four PRD steps against a local server with no restart |
| B4 | 7 to 9 | Judge simulator: scenario families, seeded generator, runner (in-process and over HTTP), PRD scorecard, tuning and held-out seeds | B2 | Produces a scorecard for the current build; trick rows may fail until B5 |
| B5 | 9 to 12 | Trust rules: reporter and connection clustering, copied-note merging, coordinated-burst cap, weights, verdict thresholds, `429`, challenge cap; report status `counted`, `merged`, `suspect`; all thresholds in `trust_config.py` | B4 | Held-out scorecard meets every threshold in the simulator table; metamorphic tests pass |
| B6 | 12 to 14 | `GET /map` (radius, window, severity, area points) and `GET /alerts` (`SPIKE`, `NEW_TYPE` on counted reports); `POST /challenges` | B5 | Map, alert and challenge families pass on held-out seeds; trick families raise no alerts |
| B7 | 14 to 16 | Scanners: responses, logs, database, wording (API), hardcoding; fuzzing `POST /reports`; concurrency test; coverage of `api/app/core` and `api/app/license` at 90% or more | B6 | Every scanner passes after a full simulator run; no `5xx` from fuzzing |
| B8 | 16 to 18 | Performance: 100k reports loaded, lookup and report latency over HTTPS from outside; index tuning | B6, A0 | Lookup p95 under 300 ms over HTTPS; in-process p95 under 20 ms |
| B9 | 18 to 20 | README sections on trust rules and the licence (with A); final held-out run on the deployed server; make the two licence files | all | `verify_deployed.sh` passes on the final deploy |

**Person A: web app, deployment, UI tests**

| ID | Hours | Task | Needs | Done when |
| --- | --- | --- | --- | --- |
| A0 | 0 to 2 | Pick the host (always on, persistent volume, HTTPS), deploy B0's container, set HMAC secrets, mount the volume; scaffold the web app (Vite, React, TypeScript, Tailwind, Biome) served by the API; `verify_deployed.sh` checks `/health` | B0 | `https://<host>/health` returns `{"ok": true}` and the web shell loads on a phone |
| A1 | 2 to 5 | Check screen: one input, type auto-detected, pasted messages split by the extractor; verdict card in English and Hindi with "Reported by N people near you", masked value, evidence, challenged and verified badges, "Call 1930" and cybercrime.gov.in | B1 | Works against fixtures and the stub; extractor passes `extract.json` |
| A2 | 5 to 8 | Report screen, icon first: channel icons, time quick-picks producing ISO times with `+05:30`, paste identifier, scam type icons, area by name (remembered), random device id as `reporter_id`; friendly `400` and `429` messages; "I got this too" pre-fill | B2 | A Playwright run posts a valid PRD report in under 20 seconds of scripted time |
| A3 | 8 to 10 | Complete Hindi dictionary; icon-only mode; wording scan over both dictionaries | A2 | Every string exists in both languages; no banned words |
| A4 | 10 to 12 | Map screen (Appendix B points, days and radius, severity colours, alerts for an area); Challenge screen; Licence screen and the expired screen on any `LICENSE_EXPIRED` | B3, B6 stub | Each screen works against the deployed API |
| A5 | 12 to 15 | UI test suite (below), run locally and against the deployed address | A4 | Zero console errors; all UI tests pass on a phone-sized viewport in English, Hindi and icon-only mode |
| A6 | 15 to 17 | Deployed verification loop: `verify_deployed.sh` after every deploy; results appended to `docs/RESULTS.md`; licence demo rehearsed three times on the real server | B6 | Three clean licence demos in a row, each recovering within a minute |
| A7 | 17 to 20 | README (run steps, screenshots), demo video up to 3 minutes, pitch, submission checklist | all | A teammate who has not seen the repo runs it from the README alone |

## Testing

Every layer runs locally in `scripts/check.sh`. Layers 2 to 8 also run against the HTTPS address in `scripts/verify_deployed.sh` after every deploy. That script resets the server first, so never run it after the judges have loaded data.

| # | Layer | What it proves | How | Pass threshold |
| --- | --- | --- | --- | --- |
| 1 | Unit and property | Normaliser, validation, masking, verdict and time windows are right for any input, not only examples | pytest plus Hypothesis: generate random valid numbers, UPI IDs, links and sender IDs, format each many ways, assert one standard form; generate junk and assert `400`; 1,000 or more examples per property | All pass |
| 2 | Contract | Every route matches PRD Appendix A exactly | `judge/contract.py`: each route, each status code, schema-validated replies, `NO_REPORTS` is `200`, defaults for `days` and `radius_km` | All pass, in-process and deployed |
| 3 | Judge simulator | Trust rules, map and alerts behave like the judges expect on data we have not tuned on | Scenario families below, generated from seeds; tune only on seeds 1 to 10, report on held-out seeds 101 to 150, with fresh random identifiers, reporters and prefixes every run | Thresholds in the family table |
| 4 | Metamorphic | Answers do not depend on things that should not matter | Same scenario re-run with: identifiers in other formats, reports shuffled, junk and rate-limited reports added, notes switched between English and Hindi, times written with other offsets | Verdicts, counts and alerts identical |
| 5 | Privacy scanners | Nothing identifies a reporter, anywhere | After a full simulator run: replies never contain `reporter_id`, `ip_prefix`, notes or coordinates other than area points; unmasked values only at 3 or more reporters; every log line free of identifiers, reporter fields, notes, emails and query strings; database free of raw identifiers, reporter fields and note text | Zero findings |
| 6 | Licence | The four-step demo works and cannot be cheated | Valid licence works; tampered `expires_at` rejected; wrong key rejected; expiry mid-run gives `403 LICENSE_EXPIRED` everywhere except `/health` and `/license`; `POST /license` restores service with no restart; licence survives a restart; clock set back is refused; data unchanged after expiry and renewal; licence survives `/admin/reset` | All pass, in-process with an injected clock and deployed with `license_demo.sh` |
| 7 | Performance | Lookups stay under half a second for the judges | `judge/perf.py` from a machine outside the host: 100k reports loaded, 2,000 lookups and 500 reports; also one request after 15 idle minutes | Lookup p95 under 300 ms over HTTPS; no cold start over 1 s |
| 8 | UI | Reporting is easy and the screens never break | Playwright on a phone-sized viewport: full report in English, in Hindi, and with labels hidden (icons only); Check, Map, Challenge and Licence screens; expired screen; zero console errors | All pass; scripted report under 20 s; three people new to the app report in under 60 s by stopwatch, times recorded in `RESULTS.md` |
| 9 | Anti-hardcoding | Rules work on the judges' secret data | Scanner fails on any literal phone number, UPI ID, link or sender ID in `api/app` outside `shared/data`; held-out seeds only in reported results | Zero findings |
| 10 | Robustness | Bad input never crashes the server | Hypothesis fuzzing of `POST /reports` and `GET /lookup` bodies and queries; 50 concurrent reports on one identifier; reset then lookups | No `5xx`; counts exact under concurrency; empty state after reset |
| 11 | Coverage | Tests reach the code that decides verdicts | pytest-cov on `api/app/core` and `api/app/license` | 90% lines or more |

**Judge simulator families**

| Family | Scenario | Expected |
| --- | --- | --- |
| T1 Report-bombing | 40 reporters on a real business number within an hour; variants: one prefix, 10 prefixes, 40 prefixes; notes copied, empty or lightly edited; incident times bunched | Never `KNOWN_SCAM`; no alert |
| T2 Fake accounts | 22 reporter ids on one prefix within 2 hours | `distinct_reporters` 1; never `KNOWN_SCAM` |
| T3 Spamming | One reporter 6 times in an hour; variants: other prefixes, other notes | `distinct_reporters` 1; `429` after 3 allowed |
| T4 Junk | `12345`, `test`, empty, malformed UPI and links, wrong type for the value, unknown pincode, bad or future time | `400`; nothing stored |
| T5 Verified under attack | Bombing `1930`, `HDFCBK`, `freshbakes@okaxis` and the other Appendix C values | Always `VERIFIED_BUSINESS` |
| R1 Real campaign | 5 to 60 unrelated reporters, separate prefixes, own words in English, Hindi and Hinglish, spread over 1 to 14 days and several areas | `KNOWN_SCAM`; unmasked once 3 or more |
| R2 Real sudden wave | 10 to 20 reporters within 3 hours, separate prefixes, own words, incident times spread | `KNOWN_SCAM` |
| R3 Small real | 1 or 2 reporters | `SUSPICIOUS`, masked |
| F1 Formats | Every identifier sent and looked up in every PRD format | One case per identifier; identical answers |
| M1 Map window | Reports 6, 8, 30 and 45 days old; areas 1.9 km and 2.1 km away; other cities | Only in-window, in-radius areas, at Appendix B points |
| A1 Spike | Steady 2 a day then 10 in 24 h; steady areas; exactly double with 5; double with only 4 | Alerts exactly where the PRD rule says |
| A2 New type | New type in 24 h; same type seen 29 and 31 days ago | `NEW_TYPE` only when unseen in the 30 days before |
| A3 Fakes never alert | T1 to T3 aimed at a quiet area | No alerts |
| C1 Challenge | Challenge on a number with a real campaign | `challenged: true`, never `KNOWN_SCAM` |
| Z1 Reset | Reset after any family | Every lookup `NO_REPORTS`, map and alerts empty, licence intact |

Thresholds on held-out seeds: T families 0 failures; T5, F1, M1, A1, A2, A3, C1 and Z1 100%; R1 95% or more; R2 90% or more; R3 100%. The scorecard prints an estimate per PRD row and lists every failing scenario with its seed, so a failure can be replayed.

## Sync points

1. **Hour 2, live and frozen.** `/health` is on HTTPS (A0) and the contract is merged (B1). From here, changes follow the contract rule.
2. **Hour 5, first real loop.** A report from the phone, then its lookup, on the deployed server.
3. **Hour 7, licence on the server.** The four-step demo works on HTTPS.
4. **Hour 12, trust rules meet the simulator.** Held-out scorecard reviewed together; thresholds tuned only on tuning seeds.
5. **Hour 16, feature freeze.** Only fixes, tests, performance and polish.
6. **Hour 19, rehearsal.** Clean deploy, `verify_deployed.sh`, licence demo three times, demo video recorded.

## Working with Claude Code

Claude Code gets the rules from `CLAUDE.md`, the plan from `docs/SPEC.md`, the contract from `docs/PRD.pdf` and `shared/contract`, and one task ID per session.

**Per task**

1. `git switch -c b/B5 main` (or `a/A2`, and so on).
2. Start Claude Code at the repo root and paste the task prompt below with the ID filled in.
3. Approve its plan before it writes code.
4. Read the diff, run `scripts/check.sh` yourself, then merge to `main`. A change under `shared/` waits for the other person's OK.
5. After a deploy, run `scripts/verify_deployed.sh <https address>` (it resets the server).

**Task prompt**

```text
Work on task B5 from docs/SPEC.md. Read CLAUDE.md, docs/PRD.pdf and that task's row first.
Show me a short plan before writing code.
Write the tests for the task's "Done when" column and the matching rows of the Testing section first, then make them pass.
Run scripts/check.sh until it is clean. Do not silence warnings or loosen a threshold to make a test pass.
Finish with what changed, what you could not do, and any contract change.
```

**`CLAUDE.md`** (repo root)

```markdown
# Community Scam Map

docs/PRD.pdf is the source of truth. Then docs/SPEC.md, docs/ARCHITECTURE.md, docs/DECISIONS.md.
Work only on the task ID you were given, inside its owner's folders:
A owns web/, infra/ and scripts/verify_deployed.sh; B owns api/, judge/ and the rest of scripts/.
shared/ is a contract: change it only with the other person's OK.

## Commands
- Local gate: scripts/check.sh (must pass before any commit)
- Deployed gate: scripts/verify_deployed.sh https://<host> (resets the server)
- API: cd api && uv run uvicorn app.main:app --reload
- Simulator: cd judge && uv run python runner.py --seeds holdout --target local
- Web: cd web && npm ci && npm run dev

## Rules
- Routes, request and reply fields exactly as PRD Appendix A. Extra reply fields are fine; never rename or drop one.
- No login, signature or proof-of-work on the PRD routes. Rate-limit reporters with 429 only.
- Never store or log a reporter's name, phone, reporter_id, ip_prefix or exact location. Store reporter fields only as keyed HMACs; store notes only as fingerprints.
- No request bodies, query strings, identifiers, notes or claimant contact in any log line.
- Mask display_value until 3 distinct reporters. Wording: "Reported by N people near you"; never "scammer" or "fraud".
- No hardcoded identifiers in api/app. Numbers, UPI IDs, links and sender IDs live only in shared/data.
- Tune trust thresholds on tuning seeds only; report results on held-out seeds only.
- The licence private key never enters the repo or the server. The licence is checked on every request and renewed without a restart. Expiry locks; it never deletes.
- All code is written during the event. Do not copy code from earlier projects or from ScamShield India.
- Zero warnings and errors: lint, types, build, tests, browser console. Fix causes; never add ignore comments.
- No new dependency unless npm audit or pip-audit shows 0 findings with it. Pin exact versions.
- Write the task's tests first; the task is done only when they pass.
```

**`scripts/check.sh`**

```bash
#!/usr/bin/env bash
# Local zero-warning gate.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Repo scans"
if git ls-files | grep -E '\.key$|\.env$' ; then echo "secret file tracked"; exit 1; fi
if git grep -n "BEGIN PRIVATE KEY" -- . ':!docs' ':!scripts/check.sh' ':!scripts/license_keygen.py' ; then echo "private key in repo"; exit 1; fi

echo "== API"
(cd api
  uv sync --frozen
  uv run ruff check .
  uv run ruff format --check .
  uv run mypy --strict app
  uv run pytest -q -W error --cov=app/core --cov=app/license --cov-fail-under=90
  uv run pip-audit)

echo "== Judge (in-process, held-out seeds)"
(cd judge
  uv sync --frozen
  uv run ruff check .
  uv run mypy --strict .
  uv run python contract.py --target local
  uv run python runner.py --seeds holdout --target local --fail-under-thresholds
  uv run python -m scanners.all --target local
  uv run pip-audit)

echo "== Web"
(cd web
  npm ci --no-fund
  npm audit --audit-level=low
  npx biome ci --error-on-warnings .
  npx tsc --noEmit
  npm run build 2>&1 | tee /tmp/web-build.log
  if grep -qi "warn" /tmp/web-build.log; then echo "build warnings"; exit 1; fi
  npx playwright test)

echo "check passed on $(date -u +%F)"
```

The audits are a snapshot, so run the script again right before submitting and record the date it passed in `docs/RESULTS.md`.

## Dependencies

Audited on 31 Oct with no findings: FastAPI, uvicorn, cryptography, httpx, pytest, pytest-cov, Hypothesis, jsonschema, ruff and mypy for Python (pip-audit). For the web: React, React Router, TanStack Query, Leaflet, react-leaflet, Vite, Tailwind, Biome, TypeScript and Playwright (137 packages, npm audit). Anything else needs the same check first.

## Cut order

If time runs short, drop from the top. Everything after "Not cut" is scored or protects against disqualification.

1. Lookalike link hints
2. Pasted-message splitting (keep the single-identifier input)
3. Map tiles (points on a plain background stay)
4. How-it-works screen polish
5. Extra Bengaluru areas from the datameet file (Appendix B areas stay)
6. Challenge screen polish (the `POST /challenges` route stays: 2 bonus points)

Not cut: the PRD routes, normalisation, trust rules, masking, verified numbers, the licence with hot swap, HTTPS deployment, the Hindi and icon report screen, and test layers 1 to 6.

## Demo and submission

**Live licence demo (what the judges ask for):**

1. Open the app on the phone and show `GET /license`: licensee and expiry.
2. Upload the licence that expires in 5 minutes.
3. After 5 minutes, a lookup fails and the app shows "Licence expired. Contact your provider."
4. Upload the long licence; the app works again within a minute, with the old data still there.

**Demo video (up to 3 minutes):** a Hindi report from the phone in under 60 seconds; a lookup showing "Reported by N people near you" and a masked value; a verified bank number; the 40-friends bomb failing to make a bakery a known scam, from the simulator; the map and a spike alert; the licence demo.

**Submit:** the Git repository; the HTTPS address, working during judging; the mobile website link; the README (run steps, trust rules, licence); the demo video; two licence files (5-minute and long), with the private key kept off the repo.
