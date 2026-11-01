"""Builds docs/Hackathon-Brief.pdf: submission checklist, system design, judge Q&A, scoring, demo notes.

Run: uv run --with reportlab python docs/make_brief.py
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

GREEN = colors.HexColor("#00a86b")
INK = colors.HexColor("#1c1c1c")
TINT = colors.HexColor("#eefaf4")
OUT = Path(__file__).with_name("Hackathon-Brief.pdf")

base = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=base["BodyText"], fontSize=9, leading=12, textColor=INK)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8, leading=10)
H1 = ParagraphStyle("h1", parent=base["Heading1"], fontSize=20, textColor=INK, spaceAfter=2)
H2 = ParagraphStyle(
    "h2", parent=base["Heading2"], fontSize=12.5, textColor=GREEN, spaceBefore=10, spaceAfter=4
)
Q = ParagraphStyle("q", parent=BODY, fontName="Helvetica-Bold", spaceBefore=4)


def p(text: str, style: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(text, style)


def table(rows: list[list[str]], widths: list[float], header: bool = True) -> Table:
    data = [[p(c, SMALL) for c in row] for row in rows]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d6cf")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), TINT)]
    t.setStyle(TableStyle(style))
    return t


def bullets(items: list[str]) -> list[Paragraph]:
    return [p("&bull; " + i) for i in items]


def qa(question: str, answer: str) -> KeepTogether:
    return KeepTogether([p(question, Q), p(answer)])


story: list = [
    p("Community Scam Map", H1),
    p("Hackathon brief: what we submit, how it works, and what judges may ask", BODY),
    Spacer(1, 4),
    p("1. What to submit (hosting is on localhost)", H2),
    table(
        [
            ["Item", "Our answer", "Status"],
            ["Code in a Git repository", "Branch <b>shubhang</b>; <b>scripts/check.sh</b> must pass.", "Commit and push the open changes"],
            ["Server public web address", "Laptop on the judges' Wi-Fi: <b>http://&lt;laptop-ip&gt;:8000</b>. Printed by <b>scripts/run_local.sh</b>. Needs the firewall rule from infra/README.", "Test from a second device. Plain http, not https: confirm with organisers"],
            ["App: APK or mobile website", "Mobile website (Streamlit) on port <b>8501</b>. No APK.", "Done"],
            ["README: run, trust rules, licence", "README.md covers all three, plus known limits.", "Done"],
            ["Demo video, up to 3 min", "Record: check a number, report, map and alerts, licence expiry and renewal.", "<b>Not made yet</b>"],
            ["Two licence files", "Long: <b>.local/demo/licence-long.json</b> (valid to Nov 2027). 5-minute: sign it just before the demo.", "5-minute file made on the day"],
        ],
        [38, 92, 46],
    ),
    Spacer(1, 4),
    p("Sign the 5-minute licence (its expiry time is absolute, so a file made earlier is already dead):", SMALL),
    p("<font face='Courier' size='7.5'>uv run --project api python scripts/license_sign.py --licensee \"Demo Bank\" --expires-in 5m --out .local/demo/licence-5min.json</font>", SMALL),
    p("2. System design", H2),
    table(
        [
            ["Layer", "What it is", "Key point"],
            ["Mobile website", "Streamlit, port 8501. Screens: Check, Report, Map, Dispute, Licence, How it works. Live right-hand panel of alerts and events, refreshed every 3 s. English and Hindi.", "Talks to the API only; holds no data"],
            ["API", "FastAPI, port 8000. Exactly the PRD routes: /health, /reports, /lookup, /map, /alerts, /admin/reset, /challenges, /license. Two UI-only routes: /app/areas, /app/activity.", "No login, no proof-of-work; only 429 rate limits"],
            ["Trust engine", "Collapses repeats, merges copied notes, caps bursts, scores independent clusters, gives a verdict.", "All thresholds in trust_config.py"],
            ["Licence gate", "Ed25519 signature checked on every request. Hot-swap with POST /license, no restart. Expiry returns 403 LICENSE_EXPIRED; data is never deleted.", "Private key never on the server"],
            ["Storage", "SQLite (WAL). Reporter, network prefix and identifiers stored only as keyed HMAC; notes only as MinHash fingerprints.", "No request log lines at all"],
        ],
        [30, 106, 40],
    ),
    Spacer(1, 4),
    p("<b>Flow:</b> phone &rarr; website &rarr; API (licence check &rarr; validate &rarr; hash identifiers &rarr; trust rules &rarr; store) &rarr; lookup, map and alerts read only <b>counted</b> reports.", BODY),
    p("3. Points division and where it is earned", H2),
    table(
        [
            ["PRD row", "Pts", "How we earn it", "Proof"],
            ["1 Stops fake reports", "20", "Reporter and network dedupe, copied-note merge, burst cap, 429 above 3 reports/hour", "15 simulator families; held-out 750/750"],
            ["2 Lookup is right", "15", "Verdict from independent clusters; masked until 3 reporters; verified list", "Datasets; p95 latency tests"],
            ["3 Map and alerts", "10", "Spike and new-type alerts on counted reports only; 30-day window", "Map and alert families"],
            ["4 Privacy", "15", "HMAC only, fingerprints only, no logs, careful wording", "5 scanners: 0 findings; privacy check"],
            ["5 Server and licence", "15", "Live 4-step demo; reachable address", "Licence tests; <b>no https</b>, so partly proven"],
            ["6 Usability", "15", "Icon-first mobile screens, under 20 s to report", "<b>Judged by people; stopwatch test pending</b>"],
            ["7 Demo and pitch", "10", "Clear 3-minute story", "<b>Judged by people; video pending</b>"],
            ["Bonus", "7", "Verified numbers 3, disputes 2, fakes never alert 2", "Contract checks"],
        ],
        [32, 10, 78, 56],
    ),
    p("Total 100 + 7 bonus = 107. Our tools measure rows 1 to 5 and the bonus: 82.0 of 82. Rows 6 and 7 (25 points) depend on people, so the demo matters most.", SMALL),
    p("4. Questions a recruiter or judge may ask", H2),
    qa("Why can't someone just spam reports to brand a number a scam?",
       "One reporter counts once. Same network within 24 hours counts once. Copied notes merge. A burst of new reporters is capped as a single cluster. A known scam needs 3 independent clusters and a score of 3.0."),
    qa("Why did you not use a login or proof-of-work?",
       "The PRD forbids both on the report routes. We rate-limit with 429 and rely on the trust rules."),
    qa("How do you protect privacy if you still need to spot repeats?",
       "We keep keyed hashes, so the same value matches without being readable. Notes become fingerprints that detect similarity but cannot be read back. Nothing is logged."),
    qa("What does 'verified business' mean?",
       "Only that the value is on the organisers' Appendix C list. We do not check real-world identity."),
    qa("What happens when the licence expires mid-demo?",
       "Every route except /health and /license returns 403 LICENSE_EXPIRED. Uploading a new licence restores service at once with all data intact. A rolled-back clock also counts as expired."),
    qa("Can the verdict be wrong?",
       "Yes. A coordinated attack with many real-looking, varied reporters can still push a score, so we show counts, not accusations, and allow one dispute per number."),
    qa("How do you know it works?",
       "Seeded black-box simulator of 15 scenario families, tuned on tuning seeds and reported on held-out seeds only; five PRD-format datasets loaded with plain curl; 432 API, 197 web and 265 judge tests."),
    qa("What is your weakest point?",
       "Public https (we are on http over Wi-Fi), rows 6 and 7 not yet tested with real people, and the verified list being a static file."),
    p("5. Can judges inject data? How feasible?", H2),
    p("There are no log files to inject into: by design we write <b>no per-request logs</b>, so nothing a judge sends can be read back from a log. Injecting <b>reports</b> is fully supported and is the intended test."),
    *bullets(
        [
            "Anyone on the Wi-Fi can call the PRD routes with plain <b>curl</b>: POST /reports, GET /lookup, /map, /alerts.",
            "<b>POST /admin/reset</b> wipes the data, as the PRD requires; <b>POST /license</b> swaps the licence. Neither needs a login, so keep the laptop on a trusted network.",
            "Verified: we erased the database and loaded all five datasets with curl only: 116 of 116 checks, 82.0 of 82.",
            "Limits: heavy load from one source gets 429, and a very large load is bounded by one laptop (SQLite).",
        ]
    ),
    p("6. Notable rule: reports from outside the city count for less", H2),
    p("<b>Idea:</b> a report from outside a number's home city carries reduced weight, unless people from that city have also reported the same business or person."),
    *bullets(
        [
            "<b>Rule:</b> each report is tagged with its area's city. Out-of-city reports weigh about 0.5 until at least one in-city independent cluster exists; then they count fully.",
            "<b>Why:</b> a distant attacker cannot brand a local shop alone, but a real scam that travels (online, calls) is still confirmed once locals agree.",
            "<b>Feasibility:</b> high. Reports already carry an area (PRD Appendix B). It needs a city per area, one extra weight in trust_config.py, and tests. About half a day.",
            "<b>Status:</b> <b>not built yet.</b> It is a design proposal, and it needs the PRD to allow it for online-only scams (phone numbers and links have no city).",
        ]
    ),
    p("7. Future scope", H2),
    *bullets(
        [
            "Public https hosting and a proper domain; an Android APK.",
            "Per-city trust weighting (above), and reporter reputation that does not need an identity.",
            "A review queue for disputes and a signed, updatable verified-business list.",
            "Move from SQLite to Postgres and add caching for many cities.",
            "More languages; push notifications for alerts near a user.",
            "Share confirmed scams with banks and telecom partners.",
        ]
    ),
    p("8. Demo essentials", H2),
    *bullets(
        [
            "Before: run <b>scripts/run_local.sh</b>, test the laptop address from a phone, open the firewall rule, plug in power, stop sleep.",
            "Sign the 5-minute licence about one minute before the licence step.",
            "Order (3 minutes): check a known-scam number &rarr; report a new one &rarr; map and live panel &rarr; dispute &rarr; licence: upload 5-minute file, wait, see 403, upload long file, data intact.",
            "Say plainly: nothing is logged, personal details are hashed, wording is 'reported by N people', never 'scammer'.",
            "Backup: keep a recorded video and the curl commands in <b>.local/curl/</b>. Rehearse three times.",
            "Be honest about limits: http not https, verified means 'on the list'.",
        ]
    ),
]

doc = SimpleDocTemplate(
    str(OUT),
    pagesize=A4,
    leftMargin=16 * mm,
    rightMargin=16 * mm,
    topMargin=14 * mm,
    bottomMargin=14 * mm,
    title="Community Scam Map brief",
)
doc.build(story)
print(OUT)
