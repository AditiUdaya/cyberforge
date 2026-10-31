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
- Web: cd web && uv run streamlit run app.py (Streamlit, DECISIONS D54; reads SCAM_MAP_API_URL)

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
- No new dependency unless pip-audit shows 0 findings with it. Pin exact versions.
- Write the task's tests first; the task is done only when they pass.
