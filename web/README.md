<!-- Mobile website: Streamlit, Python 3.12 (DECISIONS D54). Owner: A. Filled in by: A0 to A5. -->
# web

The mobile website, in Streamlit. It talks to the API at `SCAM_MAP_API_URL` and runs as its own service
(DECISIONS D55). Locally: http://127.0.0.1:8501 via `scripts/run_local.sh`.

| Screen | What |
| --- | --- |
| Check (home) | Paste a value or a whole message; one verdict card per identifier found |
| Report | Icon first: channel, when, the identifier, scam type, area. No login. |
| Map | Area points by count and severity; days and distance; alerts for the area |
| Dispute | A business says "this is our real number" |
| Licence | Who it is licensed to and until when; upload a licence file |
| How it works | The trust and privacy rules in plain words |

Every screen has a **live panel** on the right (below the content on a phone), refreshed every 3 seconds: live
alerts for all areas, then every event: reports counted, repeats merged, coordinated bursts, junk rejected,
reporters slowed down, new known scams, disputes and alerts. Numbers are always masked there.

Every screen works in English and Hindi, and with icons only. Any `LICENSE_EXPIRED` reply shows
"Licence expired. Contact your provider."

```bash
uv sync --frozen && SCAM_MAP_API_URL=http://127.0.0.1:8000 uv run streamlit run app.py
```

```bash
uv run pytest -q -W error
```

`scam_web/normalise.py` is a copy of the API's normaliser for the message extractor; both must pass every case in
`shared/vectors/normalise.json`.
