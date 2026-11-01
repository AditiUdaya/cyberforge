"""Builds the evaluation datasets in judge/datasets/: PRD Appendix A reports plus expected outcomes.

    uv run python build_datasets.py

Every report is exactly the PRD's POST /reports body and every dispute its POST /challenges body.
Each file also lists what a correct server must answer, tagged with the PRD scoring row it counts
toward; score_dataset.py loads a file into a server and scores it. Times are written relative to
the moment of building ("_anchor"); the scorer shifts them so the file never goes stale.

Owner: B. Filled in by: B9.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from generator import IST, Gen, Person, ReportStep, areas, distance_km, phone_formats, verified

OUT = Path(__file__).resolve().parent / "datasets"
ANCHOR = datetime.now(UTC).replace(second=0, microsecond=0)

HINDI_NOTES = [
    "आज सुबह एक आदमी ने खुद को पुलिस बताया और कहा मेरे नाम पर पार्सल में ड्रग्स मिले हैं, 50000 मांगे",
    "मेरे पिताजी को वीडियो कॉल आया, वर्दी में आदमी था, बोला गिरफ्तार कर लेंगे, तीन घंटे बात की",
    "Bhai ye number se call aaya, bola KYC expire ho gaya, link bheja, maine kuch nahi bataya",
    "Mummy ko call aaya ki SIM band ho jayega, OTP maang raha tha, unhone phone kaat diya",
    "कॉलर ने कहा बिजली कट जाएगी आज रात, एक यूपीआई आईडी पर पैसे भेजने को बोला",
]


class Dataset:
    def __init__(self, number: int, name: str, about: str) -> None:
        self.g = Gen(f"dataset{number}", number, "v1", ANCHOR)
        self.number, self.name, self.about = number, name, about
        self.reports: list[dict[str, Any]] = []
        self.statuses: dict[str, list[int]] = {}
        self.challenges: list[dict[str, Any]] = []
        self.challenge_statuses: list[list[int]] = []
        self.expect: list[dict[str, Any]] = []

    # ---------------------------------------------------------------- adding data
    def add(self, step: ReportStep) -> dict[str, Any]:
        self.reports.append(step.body)
        if step.expect != frozenset({201}):
            self.statuses[step.body["report_id"]] = sorted(step.expect)
        return step.body

    def campaign(
        self,
        kind: str,
        normalised: str,
        people: int,
        *,
        days: float,
        pincodes: list[str] | None = None,
        notes: list[str] | None = None,
        scam_type: str = "digital-arrest",
        spellings: list[str] | None = None,
    ) -> None:
        """Unrelated people, own connections and words, incidents spread over `days`."""
        g = self.g
        spellings = spellings or g.spellings(kind, normalised)
        for i, person in enumerate(g.people(people)):
            note = notes[i % len(notes)] if notes else g.note()
            self.add(
                g.report(
                    person,
                    kind,
                    g.rng.choice(spellings),
                    occurred=g.ago(hours=2) - timedelta(days=days) * g.rng.random(),
                    pincode=g.rng.choice(pincodes) if pincodes else None,
                    note=note,
                    scam_type=scam_type,
                )
            )

    def counted(self, pincode: str, hours: list[float], scam_type: str) -> None:
        """Reports the trust rules count: each a new person and number, in their own words."""
        g = self.g
        for age in hours:
            self.add(
                g.report(
                    g.person(),
                    "phone",
                    f"+91 {g.mobile()}",
                    occurred=g.ago(hours=age),
                    pincode=pincode,
                    scam_type=scam_type,
                    delay_minutes=g.rng.uniform(2, min(30.0, age * 30)),
                )
            )

    def bomb(
        self,
        value: str,
        pincode: str,
        *,
        friends: int = 40,
        prefixes: int = 1,
        notes: str = "copied",
        scam_type: str = "fake-customer-care",
    ) -> None:
        """Friends of a rival reporting a real business within an hour, one story, one moment."""
        g = self.g
        pool = [g.prefix() for _ in range(prefixes)]
        script = g.note()
        incident = g.ago(hours=g.rng.uniform(3, 10))
        for i in range(friends):
            note = {"copied": script, "empty": "", "edited": script + f" pls share {i % 3}"}[notes]
            self.add(
                g.report(
                    g.person(pool[i % prefixes]),
                    "phone",
                    value,
                    occurred=incident + timedelta(minutes=g.rng.uniform(0, 14)),
                    pincode=pincode,
                    note=note,
                    scam_type=scam_type,
                    delay_minutes=15 + i * 1.1,
                )
            )

    def challenge(self, kind: str, value: str, name: str, status: int = 201) -> None:
        self.challenges.append(
            {
                "identifier_type": kind,
                "identifier_value": value,
                "claimant_name": name,
                "contact_email": f"owner{len(self.challenges) + 1}@example.com",
                "proof_note": "GST certificate and shop licence attached.",
            }
        )
        self.challenge_statuses.append([status])

    # ---------------------------------------------------------------- expectations
    def lookup(self, row: str, label: str, kind: str, value: str, **want: Any) -> None:
        self.expect.append(
            {"kind": "lookup", "row": row, "label": label, "type": kind, "value": value} | want
        )

    def lookup_400(self, row: str, label: str, kind: str, value: str) -> None:
        self.expect.append(
            {
                "kind": "lookup_status",
                "row": row,
                "label": label,
                "type": kind,
                "value": value,
                "status": 400,
            }
        )

    def same_answer(self, row: str, label: str, kind: str, values: list[str]) -> None:
        self.expect.append(
            {"kind": "same_answer", "row": row, "label": label, "type": kind, "values": values}
        )

    def map(
        self,
        row: str,
        label: str,
        pincode: str,
        *,
        pincodes: dict[str, int | None] | None = None,
        absent: list[str] | None = None,
        days: float | None = None,
        radius_km: float | None = None,
    ) -> None:
        """pincodes: exactly the areas on the map, with counts (None: any count);
        absent: areas that must not be on it."""
        params = {k: v for k, v in (("days", days), ("radius_km", radius_km)) if v is not None}
        self.expect.append(
            {
                "kind": "map",
                "row": row,
                "label": label,
                "pincode": pincode,
                "params": params,
                "pincodes": pincodes,
                "absent": absent or [],
            }
        )

    def alerts(
        self, row: str, label: str, pincode: str, *, spike: bool, new_types: list[str] | None
    ) -> None:
        """new_types None: only the spike is checked."""
        self.expect.append(
            {
                "kind": "alerts",
                "row": row,
                "label": label,
                "pincode": pincode,
                "spike": spike,
                "new_types": new_types,
            }
        )

    def write(self) -> Path:
        OUT.mkdir(exist_ok=True)
        path = OUT / f"{self.number:02d}_{self.name}.json"
        doc = {
            "_about": self.about,
            "_anchor": ANCHOR.isoformat(),
            "_schema": "reports: PRD Appendix A POST /reports bodies; challenges: POST /challenges",
            "reports": self.reports,
            "expect_status": self.statuses,
            "challenges": self.challenges,
            "challenge_status": self.challenge_statuses,
            "expect": self.expect,
        }
        path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return path


def as_written(value: str) -> list[str]:
    """An Appendix C value as printed, and without its spaces (1800 1600 and 18001600)."""
    return sorted({value, value.replace(" ", "")})


def bengaluru() -> list[str]:
    return sorted(p for p, a in areas().items() if a["city"] == "Bengaluru")


def radius_pair(pins: list[str]) -> tuple[str, str]:
    """A centre and its nearest neighbour with no third area within 0.1 km of that distance,
    so "inside the radius" and "just outside it" are unambiguous."""
    for centre in pins:
        others = sorted((distance_km(centre, p), p) for p in pins if p != centre)
        (dist, near), (second, _) = others[0], others[1]
        if second > dist + 0.1 and dist > 0.2:
            return centre, near
    raise RuntimeError("no centre has a clearly separated nearest neighbour")


def steady(g: Gen, per_day: int) -> list[float]:
    return [24 + 24 * d + g.rng.uniform(1, 23) for d in range(7) for _ in range(per_day)]


def today(g: Gen, n: int) -> list[float]:
    return [g.rng.uniform(0.5, 22) for _ in range(n)]


# ---------------------------------------------------------------- 1: the four tricks


def tricks() -> Dataset:
    d = Dataset(
        1, "tricks", "The PRD's four tricks: report-bombing, fake accounts, spamming, junk."
    )
    g = d.g
    pins = bengaluru()
    elsewhere = pins[5]  # every report that is not a bomb, away from the quiet bomb areas
    for label, prefixes, notes, pin in [
        ("40 friends, one Wi-Fi, copied note", 1, "copied", pins[0]),
        ("40 friends, 40 connections, empty notes", 40, "empty", pins[1]),
        ("40 friends, 10 connections, lightly edited notes", 10, "edited", pins[2]),
    ]:
        bakery = g.landline()
        value = f"+91 {bakery[:2]} {bakery[2:6]} {bakery[6:]}"
        d.bomb(value, pin, prefixes=prefixes, notes=notes)
        d.lookup("1", f"{label}: never KNOWN_SCAM", "phone", value, not_verdict="KNOWN_SCAM")
        d.lookup("1", f"{label}: counts as one reporter", "phone", value, distinct_reporters=1)
        d.lookup("4", f"{label}: stays masked", "phone", value, display="masked")
        d.alerts(
            "bonus:fakes", f"{label}: no alert in a quiet area", pin, spike=False, new_types=[]
        )

    # 22 accounts on one Wi-Fi within 2 hours.
    _, value, normalised = g.identifier("upi")
    wifi, start = g.prefix(), g.ago(hours=6)
    for account in g.people(22, prefix=wifi):
        d.add(
            g.report(
                account,
                "upi",
                value,
                occurred=start,
                note=g.note(),
                pincode=elsewhere,
                delay_minutes=g.rng.uniform(5, 115),
            )
        )
    d.lookup("1", "22 accounts on one Wi-Fi: one reporter", "upi", normalised, distinct_reporters=1)
    d.lookup(
        "1",
        "22 accounts on one Wi-Fi: never KNOWN_SCAM",
        "upi",
        normalised,
        not_verdict="KNOWN_SCAM",
    )

    # One person six times in an hour, from one connection and from different ones.
    for label, moving in (("same connection", False), ("different connections", True)):
        _, value, normalised = g.identifier("phone")
        spammer = g.person()
        for i in range(6):
            who = Person(spammer.reporter_id, g.prefix()) if moving else spammer
            d.add(
                g.report(
                    who,
                    "phone",
                    value,
                    occurred=g.ago(hours=3),
                    pincode=elsewhere,
                    delay_minutes=8 * i + 1,
                    expect=frozenset({201}) if i < 3 else frozenset({429}),
                )
            )
        d.lookup(
            "1",
            f"6 times in an hour ({label}): one reporter",
            "phone",
            normalised,
            distinct_reporters=1,
            report_count=3,
        )

    # Junk: every report here is 400 and nothing is stored.
    real = g.mobile()
    base = g.report(
        g.person(), "phone", f"+91 {real}", occurred=g.ago(hours=5), pincode=elsewhere
    ).body
    future = (ANCHOR + timedelta(days=3)).astimezone(IST).isoformat()
    for n, change in enumerate(
        [
            {"identifier_value": "12345"},
            {"identifier_value": "test"},
            {"identifier_value": ""},
            {"identifier_value": "98765"},
            {"identifier_value": "+1 415 555 0100"},
            {"identifier_value": "+91 12345 67890"},
            {"identifier_type": "upi", "identifier_value": "ravi@@okaxis"},
            {"identifier_type": "upi", "identifier_value": "noatsign.okaxis"},
            {"identifier_type": "url", "identifier_value": "http://"},
            {"identifier_type": "url", "identifier_value": "not a link"},
            {"identifier_type": "url", "identifier_value": "javascript:alert(1)"},
            {"identifier_type": "sender_id", "identifier_value": "HDFC"},
            {"identifier_type": "upi", "identifier_value": f"+91 {real}"},
            {"identifier_type": "email", "identifier_value": "a@b.com"},
            {"pincode": "999999"},
            {"pincode": "HSR Layout"},
            {"occurred_at": "yesterday"},
            {"occurred_at": future},
            {"occurred_at": base["occurred_at"][:19]},
        ]
    ):
        body = base | change | {"report_id": f"junk_{n}"}
        d.reports.append(body)
        d.statuses[body["report_id"]] = [400]
    d.lookup("1", "junk stored nothing", "phone", f"+91{real}", verdict="NO_REPORTS")
    for kind, value in [
        ("phone", "12345"),
        ("phone", "test"),
        ("upi", "test"),
        ("url", "test"),
        ("sender_id", "X"),
        ("phone", ""),
    ]:
        d.lookup_400("1", f"lookup {kind} {value!r} is 400", kind, value)
    return d


# ---------------------------------------------------------------- 2: real scams


def real_scams() -> Dataset:
    d = Dataset(
        2, "real_scams", "Real campaigns of every type, waves, small cases, masking, formats."
    )
    g = d.g
    pins = bengaluru()

    n = g.mobile()
    d.campaign(
        "phone",
        f"+91{n}",
        12,
        days=9,
        pincodes=pins[:4],
        notes=HINDI_NOTES + [g.note() for _ in range(7)],
    )
    d.lookup(
        "2",
        "12 people, English and Hindi notes: KNOWN_SCAM",
        "phone",
        f"0{n}",
        verdict="KNOWN_SCAM",
        distinct_reporters=12,
    )
    d.lookup("4", "shown in full at 12 reporters", "phone", f"+91{n}", display="full")
    d.same_answer("2", "every PRD phone format gives the same answer", "phone", phone_formats(n))

    for kind, people in (("upi", 6), ("url", 5), ("sender_id", 4)):
        _, value, normalised = g.identifier(kind)
        d.campaign(kind, normalised, people, days=5, scam_type="fake-kyc-link")
        d.lookup("2", f"{kind} campaign by {people}: KNOWN_SCAM", kind, value, verdict="KNOWN_SCAM")
        d.same_answer(
            "2", f"{kind} spellings give the same answer", kind, g.spellings(kind, normalised)
        )

    # A real sudden wave: 15 people within 3 hours, calls spread out, own words.
    n = g.mobile()
    end = g.ago(minutes=40)
    for i, person in enumerate(g.people(15)):
        d.add(
            g.report(
                person,
                "phone",
                g.rng.choice(phone_formats(n)),
                occurred=end - timedelta(hours=3) * ((i + g.rng.random()) / 15),
                scam_type="courier-customs",
                delay_minutes=g.rng.uniform(5, 40),
            )
        )
    d.lookup(
        "2", "sudden real wave of 15: KNOWN_SCAM (not capped)", "phone", n, verdict="KNOWN_SCAM"
    )

    # Masking at 1, 2 and 3 reporters, and 3 people with empty notes.
    for people, verdict, display in (
        (1, "SUSPICIOUS", "masked"),
        (2, "SUSPICIOUS", "masked"),
        (3, "KNOWN_SCAM", "full"),
    ):
        n = g.mobile()
        d.campaign("phone", f"+91{n}", people, days=4)
        d.lookup("2", f"{people} reporter(s): {verdict}", "phone", n, verdict=verdict)
        d.lookup("4", f"{people} reporter(s): {display}", "phone", n, display=display)
    n = g.mobile()
    d.campaign("phone", f"+91{n}", 3, days=4, notes=[""])
    d.lookup(
        "2",
        "3 people, empty notes: weight 1.8, SUSPICIOUS",
        "phone",
        n,
        verdict="SUSPICIOUS",
        distinct_reporters=3,
    )
    d.lookup("4", "3 people, empty notes: shown in full (3 reporters)", "phone", n, display="full")

    # Unknown scam type and channel are accepted; scam type is stored as other.
    n = g.mobile()
    d.add(
        g.report(
            g.person(),
            "phone",
            n,
            occurred=g.ago(hours=30),
            scam_type="crypto-doubler",
            channel="Carrier pigeon",
        )
    )
    d.lookup("2", "unknown scam type stored as other", "phone", n, scam_type="other")

    # Same incident written with other time offsets.
    n = g.mobile()
    for person, tz in zip(g.people(3), (UTC, IST, IST), strict=True):
        step = g.report(person, "phone", n, occurred=g.ago(days=2))
        body = step.body | {
            "occurred_at": datetime.fromisoformat(step.body["occurred_at"])
            .astimezone(tz)
            .isoformat()
        }
        d.reports.append(body)
    d.lookup("2", "offsets Z and +05:30 for one moment: one case", "phone", n, report_count=3)

    d.lookup(
        "2",
        "unreported number is 200 NO_REPORTS",
        "phone",
        "+91 70000 12345",
        verdict="NO_REPORTS",
        display="masked",
    )
    return d


# ---------------------------------------------------------------- 3: verified and disputes


def verified_and_disputes() -> Dataset:
    d = Dataset(3, "verified_disputes", "Appendix C values under attack; disputes of every kind.")
    g = d.g
    for item in verified():
        kind, value = str(item["type"]), str(item["value"])
        d.campaign(kind, value, 8, days=6, spellings=as_written(value))
        d.lookup(
            "bonus:verified",
            f"{value} ({item['owner']}) stays VERIFIED_BUSINESS",
            kind,
            value,
            verdict="VERIFIED_BUSINESS",
        )
    d.lookup(
        "bonus:verified",
        "1800 1600 written without spaces",
        "phone",
        "18001600",
        verdict="VERIFIED_BUSINESS",
    )
    d.lookup(
        "bonus:verified",
        "sender with prefix vm-hdfcbk",
        "sender_id",
        "vm-hdfcbk",
        verdict="VERIFIED_BUSINESS",
    )

    business = g.landline()
    spaced = f"+91 {business[:2]} {business[2:6]} {business[6:]}"
    d.campaign("phone", f"+91{business}", 6, days=5)
    d.challenge("phone", spaced, "Lakshmi Stores")
    d.lookup(
        "bonus:dispute",
        "disputed number: challenged, capped at SUSPICIOUS",
        "phone",
        f"0{business}",
        challenged=True,
        verdict="SUSPICIOUS",
    )

    quiet = g.landline()
    d.challenge("phone", f"0{quiet}", "City Pharmacy")
    d.lookup(
        "bonus:dispute",
        "disputed with no reports: challenged, NO_REPORTS",
        "phone",
        f"+91{quiet}",
        challenged=True,
        verdict="NO_REPORTS",
    )
    d.challenge("phone", "+91 80 4100 2233", "Fresh Bakes")
    d.lookup(
        "bonus:dispute",
        "disputed verified number stays VERIFIED_BUSINESS",
        "phone",
        "+91 80 4100 2233",
        challenged=True,
        verdict="VERIFIED_BUSINESS",
    )
    d.challenge("phone", "12345", "Nobody", status=400)
    return d


# ---------------------------------------------------------------- 4: map and alerts


def map_and_alerts() -> Dataset:
    d = Dataset(4, "map_alerts", "Map windows, radius edge, other cities, every alert rule.")
    g = d.g
    pins = bengaluru()
    used: set[str] = set()

    def pick() -> str:
        choice = next(p for p in pins if p not in used)
        used.add(choice)
        return choice

    centre, near = radius_pair(pins)
    dist = distance_km(centre, near)
    # Every other test area stays outside the radius checks, so only these two can appear.
    used.update(p for p in pins if distance_km(centre, p) <= dist + 0.1)

    window = pick()
    for days in (6, 8, 30, 45):
        d.counted(window, [24 * days + 3], "job-offer")
    d.map("3", "7 days: only the 6-day-old report", window, radius_km=0, pincodes={window: 1})
    d.map("3", "31 days: 6, 8 and 30 days old", window, days=31, radius_km=0, pincodes={window: 3})
    d.map("3", "60 days: all four", window, days=60, radius_km=0, pincodes={window: 4})

    d.counted(centre, [30], "otp-call")
    d.counted(near, [30], "otp-call")
    far_city = next(p for p, a in areas().items() if a["city"] == "Mumbai")
    d.counted(far_city, [30], "otp-call")
    d.map(
        "3",
        f"neighbour {dist:.2f} km away inside radius {dist + 0.1:.2f}",
        centre,
        radius_km=round(dist + 0.1, 3),
        pincodes={centre: 1, near: 1},
    )
    d.map(
        "3",
        f"neighbour outside radius {dist - 0.1:.2f}",
        centre,
        radius_km=round(max(dist - 0.1, 0), 3),
        pincodes={centre: 1},
    )
    d.map("4", "other cities never on a Bengaluru map", centre, radius_km=40, absent=[far_city])

    for label, per_day, now_n, spike in [
        ("2/day then 10 today: SPIKE", 2, 10, True),
        ("3/day then 6 (exactly double): SPIKE", 3, 6, True),
        ("2/day then 4 (double, under 5): quiet", 2, 4, False),
        ("2/day then 2 (steady): quiet", 2, 2, False),
    ]:
        pin = pick()
        d.counted(pin, steady(g, per_day) + today(g, now_n), "fake-kyc-link")
        d.alerts("3", label, pin, spike=spike, new_types=[])

    for label, earlier, new in [
        ("type never seen before: NEW_TYPE", None, ["sextortion"]),
        ("same type seen 29 days ago: quiet", 29 * 24.0, []),
        ("same type seen 31.5 days ago: NEW_TYPE", 31.5 * 24, ["sextortion"]),
    ]:
        pin = pick()
        d.counted(pin, steady(g, 1), "job-offer")
        if earlier is not None:
            d.counted(pin, [earlier], "sextortion")
        d.counted(pin, [3.0], "sextortion")
        d.alerts("3", label, pin, spike=False, new_types=new)

    quiet = pick()
    d.counted(quiet, steady(g, 1), "lottery-prize")
    bakery = g.landline()
    d.bomb(f"0{bakery}", quiet, friends=40, prefixes=1, notes="copied", scam_type="lottery-prize")
    _, value, _ = g.identifier("upi")
    wifi, start = g.prefix(), g.ago(hours=5)
    for account in g.people(22, prefix=wifi):
        d.add(
            g.report(
                account,
                "upi",
                value,
                occurred=start,
                pincode=quiet,
                scam_type="investment-group",
                delay_minutes=g.rng.uniform(5, 50),
            )
        )
    d.alerts(
        "bonus:fakes",
        "40 friends and 22 accounts in a quiet area: no alerts",
        quiet,
        spike=False,
        new_types=[],
    )

    crit = pick()
    d.counted(crit, today(g, 3) + [30 + i for i in range(9)], "otp-call")
    d.expect.append(
        {
            "kind": "severity",
            "row": "3",
            "label": "12 reports this week: CRIT",
            "pincode": crit,
            "severity": "CRIT",
        }
    )
    return d


# ---------------------------------------------------------------- 5: judging-day mix


def judging_day() -> Dataset:
    d = Dataset(5, "judging_day", "A realistic mix across all 25 areas, like the secret dataset.")
    g = d.g
    every = sorted(areas())
    mixes: dict[str, list[str]] = {}
    for pin in every:
        mix = mixes[pin] = g.rng.sample(
            [
                "digital-arrest",
                "job-offer",
                "otp-call",
                "fake-kyc-link",
                "courier-customs",
                "loan-app-harassment",
            ],
            3,
        )
        for hours in steady(g, 1):
            d.counted(pin, [hours], g.rng.choice(mix))

    campaigns = []
    for kind, people in (("phone", 25), ("upi", 9), ("url", 7), ("sender_id", 5)):
        _, value, normalised = g.identifier(kind)
        d.campaign(kind, normalised, people, days=12, pincodes=g.rng.sample(every, 4))
        campaigns.append((kind, value, people))
    for kind, value, people in campaigns:
        d.lookup("2", f"{kind} campaign by {people}", kind, value, verdict="KNOWN_SCAM")

    bakery = g.landline()
    d.bomb(f"+91{bakery}", every[3], prefixes=40, notes="empty")
    d.lookup("1", "bakery bombed by 40: not KNOWN_SCAM", "phone", bakery, not_verdict="KNOWN_SCAM")

    _, value, normalised = g.identifier("phone")
    spammer = g.person()
    for i in range(6):
        d.add(
            g.report(
                spammer,
                "phone",
                value,
                occurred=g.ago(hours=4),
                delay_minutes=7 * i + 1,
                expect=frozenset({201}) if i < 3 else frozenset({429}),
            )
        )
    d.lookup("1", "spammer: one reporter", "phone", normalised, distinct_reporters=1)

    for item in g.rng.sample(verified(), 5):
        value = str(item["value"])
        d.campaign(str(item["type"]), value, 6, days=3, spellings=as_written(value))
        d.lookup(
            "bonus:verified",
            f"{item['value']} stays verified",
            str(item["type"]),
            str(item["value"]),
            verdict="VERIFIED_BUSINESS",
        )

    spike = every[10]
    d.counted(spike, today(g, 12), mixes[spike][0])
    d.alerts(
        "3", f"{areas()[spike]['locality']}: spike of 12 today", spike, spike=True, new_types=None
    )

    for n, pin in enumerate(g.rng.sample(every, 6)):
        body = g.report(g.person(), "phone", f"+91 {g.mobile()}", occurred=g.ago(days=1 + n)).body
        tz = [UTC, IST, IST][n % 3]
        body["occurred_at"] = datetime.fromisoformat(body["occurred_at"]).astimezone(tz).isoformat()
        body["pincode"] = pin
        d.reports.append(body)
    for change in ({"identifier_value": "12345"}, {"pincode": "000000"}):
        body = g.report(g.person(), "phone", "+91 9000000000", occurred=g.ago(hours=2)).body
        body |= change
        d.reports.append(body)
        d.statuses[body["report_id"]] = [400]
    d.lookup("2", "unreported number: NO_REPORTS", "phone", "+91 71111 22222", verdict="NO_REPORTS")
    return d


def main() -> int:
    for build in (tricks, real_scams, verified_and_disputes, map_and_alerts, judging_day):
        dataset = build()
        path = dataset.write()
        print(
            f"{path.name}: {len(dataset.reports)} reports, {len(dataset.challenges)} disputes, "
            f"{len(dataset.expect)} expected outcomes"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
