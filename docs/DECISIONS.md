# Community Scam Map: Design Decisions

Oct 31, 2026 · Shubhang

What we decided for Problem 03, what each decision replaced, and why the earlier option was dropped. **The organisers' brief (`docs/PRD.pdf`, "Community Scam Map: Student Brief", 29 Oct 2026) overrides everything here.** Where a row conflicts with a later row, the later row wins; superseded rows are kept as history and marked.

Status values: **Required by PRD** · Agreed · Recommended · Needs your OK · Superseded by Dxx.

## PRD alignment (31 Oct): these override everything below

| # | Was | Now | Why | Status |
| --- | --- | --- | --- | --- |
| D36 API contract | Our own `/api/*` routes with signed, proof-of-work bodies | Exactly the PRD Appendix A routes at the root: `GET /health`, `POST /reports`, `GET /lookup`, `GET /map`, `GET /alerts`, `POST /admin/reset`, `POST /challenges`, plus `GET /license` and `POST /license`. JSON in and out as written; extra reply fields allowed. No login on these routes. UI-only helpers live under `/app/*`. | The judges' test tool scores the live server against this contract. | Required by PRD |
| D37 Reporter identity | Phone OTP plus blind-signed pseudonyms (D1, D4, D12, D24, D34) | Identity is `reporter_id` and `ip_prefix` from each report. Our web app sends a random anonymous device id; the server fills `ip_prefix` from the connection only when the body has none. Both are stored only as keyed HMACs. No phone number, no OTP, no account, nothing before the form. | The PRD gives zero for a login before the form, forbids storing a reporter's phone number, and its test tool supplies identity in the body. | Required by PRD |
| D38 Proof-of-work and signatures | Signatures and proof-of-work on reports and lookups (D23) | Dropped from every judged route. Reports are rate-limited per reporter HMAC (reply `429`, allowed by the PRD). Lookups are never throttled by connection IP, because the test tool runs from one laptop. | The test tool sends neither, and blocking it costs marks. | Required by PRD |
| D39 Pre-existing code | Reuse your earlier signing and Merkle code (D2) | All code is written during the event. Nothing from earlier projects (including SentinelEdge or the Merkle log) and no ScamShield India code. | The PRD disqualifies code written before the event. | Required by PRD |
| D40 Merkle log and moderation roles | Append-only Merkle log, moderation queue with roles (D32) | Cut. Challenges are the only review path. | Not scored, and `POST /admin/reset` must delete every report, which an append-only log fights. | Recommended |
| D41 Verdicts | High risk, Caution, No reports yet (D20) | API: `KNOWN_SCAM`, `SUSPICIOUS`, `NO_REPORTS`, `VERIFIED_BUSINESS`. UI: "Known scam", "Suspicious", "No reports", "Verified business", always worded as "Reported by N people near you", never "scammer" or "fraud". Appendix C numbers always return `VERIFIED_BUSINESS`, with a note that calls can be spoofed and nobody should share an OTP. | PRD feature 2 and lookup contract; verified numbers are worth 3 bonus points. | Required by PRD |
| D42 Counts and masking | Banded counts (D22) | Exact `report_count` and `distinct_reporters` (people after trust rules). `display_value` is masked until at least 3 distinct reporters: `98XXXXX210`, `r***@okaxis`, `sbi***.in/...`, `HD****`. `evidence` never includes reporter, IP or note. | PRD privacy rule 2 and the lookup contract. | Required by PRD |
| D43 Normalisation | 10 digits starting 6 to 9 | Phone: `+91` plus 10 digits with a leading 2 to 9 (so landlines like `+918041002233` pass); short helplines from an allowlist (`1930`, `1909`, and so on); toll-free `1800` or `1860` followed by 4 to 7 digits. UPI: lower case, no spaces. URL: `https://`, no `www.`, nothing after `?`, no trailing `/`. Sender ID: the 6-letter code without the 2-letter prefix. `12345` and `test` are `400`. | PRD Appendix A rule 3 and the Appendix C note on short and toll-free numbers. | Required by PRD |
| D44 Trust rules | Clusters, age ramp, caps (D18, D19) | One person (`reporter_id`) counts once and is rate-limited after 3 reports an hour. Reports from one `ip_prefix` within 24 hours merge into one cluster. Near-duplicate notes merge across people. A coordinated burst (first-time reporters within an hour whose notes are empty or copied, or whose incident times all fall within 15 minutes) adds at most a capped weight and is excluded from alerts; a real wave with spread incident times and own words is not capped. `distinct_reporters` is the number of independent clusters. `KNOWN_SCAM` needs at least 3 independent clusters and a weighted score of at least 3. All thresholds live in one config file and are tuned on the judge simulator's tuning seeds, then checked on held-out seeds. | Built for the four PRD tricks: 40 friends, 22 accounts on one Wi-Fi, six reports in an hour, junk. | Recommended |
| D45 Notes | Stored in reports | Only a similarity fingerprint, its length and an originality score are kept; the note text is discarded after scoring and never returned or logged. Character shingles handle English, Hindi and Hinglish alike. | PRD: personal descriptions count more than copy-paste; no personal data in logs. | Recommended |
| D46 Areas and map | 2014 datameet polygons, tap-to-pick at enrolment (D14, D27) | `GET /map` uses the 25 Appendix B points as the source of truth, plus Bengaluru pincode centroids from the datameet file as extra areas. Unknown pincodes are `400`. Radius by great-circle distance from the requested pincode's point; window by `occurred_at` against the server clock. The report form picks an area by name. | PRD: map points from Appendix B, never a reporter's location; `560102` and `560103` are not in the 2014 file. | Required by PRD |
| D47 Alerts | Poisson area test, indicator surge, entity spike | Exactly two types. `SPIKE`: trusted reports in the last 24 hours are at least double the daily average of the 7 days before, and at least 5. `NEW_TYPE`: a scam type in the last 24 hours not seen in that area in the 30 days before. Computed on trust-filtered counts only. No other types in `/alerts`. | The test tool checks these exact rules, and a fake report that sets off an alert costs bonus points. | Required by PRD |
| D48 Disputes | Dispute never lowers the level; OTP control proof (D25) | `POST /challenges` as specified. While under review, lookup shows `"challenged": true` and is never `KNOWN_SCAM` (capped at `SUSPICIOUS`). Claimant contact is stored for review only, never returned or logged, and cleared on reset. | PRD bonus feature contract. | Required by PRD |
| D49 Licence | Not in the design | Signed licence JSON (`licensee`, `expires_at`, `signature`). Ed25519 through `cryptography`, already a dependency. Public key in the code; private key only on your laptop, never in git. Checked on every request against a cached, already-verified licence. Expired: every route except `/health` and `/license` returns `403 {"error": "LICENSE_EXPIRED"}`. `POST /license` swaps in a new licence without a restart and persists it. A stored high-water time refuses a clock that goes backwards. No data is ever deleted. | PRD "Ship it" section, worth 15 points; half marks if it needs a restart. | Required by PRD |
| D50 Deployment and database | Laptop Docker Compose with Postgres (D15) | A cloud host with HTTPS from hour 2 (Render, Railway, Fly.io or a free VM), kept always on. SQLite in WAL mode on a persistent volume, so there is no network hop to the database. Postgres stays an option if the host has no volume. | PRD: real server, HTTPS, first two hours; a sleeping free tier adds cold starts that break the 0.5 second lookup. | Recommended |
| D51 Report screen | Two required fields, details after submit, enrolment first (D6, D12) | One screen, icon first: channel icons, time quick-picks (Just now, Today, Yesterday, pick), paste the number, UPI ID, link or sender, scam type icons, area by name (remembered on the device). English and Hindi. Works with icons alone. "Call 1930" and cybercrime.gov.in on every result. | PRD scores under 60 seconds, Hindi or icon use, and zero for a login before the form. | Required by PRD |
| D52 Testing | One check script and a measurement table | The test plan in `docs/SPEC.md`: unit and property tests, black-box contract tests, a judge simulator with tuning and held-out seeds, metamorphic tests, privacy scanners for responses, logs and the database, licence time-travel tests, performance over HTTPS, mobile UI tests in English, Hindi and icon-only mode, and an anti-hardcoding scan. Run locally on every change and against the deployed URL after every deploy. | You asked for rigour, and the PRD loads a secret dataset and checks for hardcoded numbers. | Agreed |
| D53 Data stance | No synthetic data, then simulated attackers labelled (D9) | Resolved: the PRD says there is no practice data and asks teams to write their own real-looking and fake reports. | PRD "What we give you". | Required by PRD |

## Earlier decisions (history)

| # | Was | Now | Why the old one was dropped | Status |
| --- | --- | --- | --- | --- |
| D1 Anonymity | Hash the phone number, or store a signing key on the server | Device keypair with a blind-signed pseudonym | Hashed phone numbers can be reversed; a server-held key lets the server forge reports. | Superseded by D37 |
| D2 Your earlier crypto | Use Kyber as the anonymity method | Reuse secp256k1 signing and the Merkle log | Kyber protects transit, not identity. | Superseded by D39 |
| D3 Duplicate reporters | IP and geolocation tracking per account | Phone quota, daily keyed network token, behaviour clustering | Shared IPs and VPNs give false matches; raw IPs break anonymity. | Superseded by D44 |
| D4 Verification | Phone or email, plus optional government ID | Phone OTP once at issuance | An ID identifies reporters; email is cheap to fake. | Superseded by D37 |
| D5 Reporter photo | Photo of the reporter | Optional screenshot of the scam | A selfie identifies the reporter. | Agreed (PRD sends only `has_screenshot`) |
| D6 Report form | Many separate inputs | Two required fields, details after submit | Fewer inputs keep a report under 60 seconds. | Superseded by D51 |
| D7 Scam types | Phishing, scam, virus, bloatware | Our ten Indian scam types | Old list did not match Indian scams. | Superseded by the PRD Appendix C list |
| D8 Build approach | FastAPI and web UI first | CLI first, Flask demo | Core first. | Superseded by D31 |
| D9 Data stance | No synthetic data | Real where it exists, simulated attackers labelled | No public India report dataset. | Superseded by D53 |
| D10 Time budget | Page metadata 23:59 IST | About 23 hours | Page date unverified. | Agreed |
| D11 Problem choice | Problem 5 | Problem 03 | Your call. | Agreed |
| D12 First-time reporting | Provisional report before OTP | Verify once, then report | One weighting path. | Superseded by D37 |
| D13 Seeded data | Raw datasets | Real URLs plus simulated phones and UPI IDs | No real report data. | Superseded by D52 (judge simulator scenarios) |
| D14 Map and area | List of pincodes | Tap on map at enrolment, snapped to pincode | No GPS. | Superseded by D46 |
| D15 Database | Graph, NoSQL or relational | Postgres, SQLite fallback, keyed HMACs | Lookup is a key read anyway. | Superseded by D50 (HMACs kept) |
| D16 Time-series add-on | Open | Not used | 14 days of data. | Agreed |
| D17 Impersonated entity | Scam type only | "Claimed to be" field | Local campaigns. | Cut (not in the PRD contract) |
| D18 Trust scoring | Reputation scoring | Clusters, age ramp, caps | Reputation herds. | Superseded by D44 |
| D19 Result tiers | Reported or unknown | 1 cluster early, 3 clusters reported | Show early reports. | Superseded by D41, D44 |
| D20 Result labels | Official, reported, unknown | High risk, Caution, No reports yet | Official could mislead. | Superseded by D41 |
| D21 Seed window | 14 days | 28 days | Weekday baseline. | Superseded by D52 |
| D22 Scraping defence | Open | Exact match, keyed hashes, banded counts, limits | Leaks. | Partly superseded by D38, D42 (exact match and keyed hashes kept) |
| D23 Proof-of-work | Optional | Adaptive proof-of-work | Raises attacker cost. | Superseded by D38 |
| D24 OTP delivery | Mocked or paid SMS | Android phone as SMS gateway | Real SMS. | Superseded by D37 |
| D25 Dispute flow | Open | OTP control proof, label only | Scammers control their numbers. | Superseded by D48 |
| D26 Seed sizes | Not set | 250 pseudonyms, 10,000 reports | Chosen by us. | Superseded by D52 |
| D27 Boundary data | Unchecked | datameet 2014 polygons | File checked. | Superseded by D46 (kept for extra Bengaluru centroids) |
| D28 Pasted-message lookup | One indicator at a time | Extract indicators on the device | People paste messages. | Agreed (UI calls `GET /lookup` once per indicator) |
| D29 Lookalike links | Not planned | Stretch hint | False positives. | Agreed (stretch) |
| D30 Spine | Three angles | A anonymous but accountable, B campaigns, C map | Fit the brief. | Revised: the spine is now trust rules that stop fakes without missing real scams, with privacy by construction; B survives as note fingerprints; C is required |
| D31 Build approach | CLI first | UI first, React web app | Your call. | Agreed (mobile website) |
| D32 Borrowed features | Not in design | Confirm, moderation, public API, sender IDs, channel, amount | Fill gaps. | Revised: "I got this too" is a normal report; moderation cut (D40); public API is the PRD API |
| D33 API framework | Flask | FastAPI | OpenAPI for free. | Agreed |
| D34 Device key curve | secp256k1 | P-256 | Browser support. | Superseded by D37 (no device keys) |
| D35 Lint and dependencies | ESLint, floating versions | Biome, pinned versions, zero-warning gate | Clean audit. | Agreed (re-audited 31 Oct with the PRD test stack: 0 findings) |

## Rules with no earlier alternative

- **Wording:** never "scammer" or "fraud". Results say "Reported by N people near you". "No reports" always says it does not mean safe.
- **Exposure:** no public list of numbers; links shown defanged; the server never fetches a reported URL.
- **Logs:** no request bodies, no query strings, no identifiers, no reporter fields, no notes, no claimant contact.
- **Time:** every window is computed from `occurred_at`, compared with the server clock, with timezone offsets respected.
- **Reset:** deletes every report, case, cluster, counter and challenge; keeps areas, verified numbers and the licence.

## Open questions

- [ ] Confirm the real submission cutoff.
- [ ] Pick the host in task A0 after checking that its free tier stays awake and offers a persistent volume.
- [ ] Should reports from pincodes outside Appendix B and the datameet list be rejected (current plan) or accepted without a map point?
- [ ] Check how this differs from Chakshu and whether Sanchar Saathi offers lookups, for the pitch.

## Sources

- `docs/PRD.pdf`: Community Scam Map: Student Brief, 29 Oct 2026 (organisers).
- MediaNama, Mar 2025: 83,668 WhatsApp accounts blocked as of 28 Feb 2025.
- MediaNama, Apr 2026: about 80 to 82% of mule accounts operate under a day.
- Inc42: digital arrest losses of ₹91.14 crore (2022), ₹339 crore (2023) and ₹1,935.51 crore (2024).
- IANS, Dec 2025: UPI fraud of ₹1,087 crore (FY24), ₹981 crore (FY25).
- Angel One, Feb 2026: Chakshu received 5.19 lakh reports in 2025.
