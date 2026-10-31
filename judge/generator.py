"""Seeded scenario generator: fresh random identifiers, reporters and prefixes every run.

A scenario is generated from (family, seed, salt): the same three always give the same reports,
so any failure can be replayed. A new salt each run gives fresh identifiers and people.
Times are relative to `now`, because the server compares occurred_at with its own clock.

Owner: B. Filled in by: B4.
"""

from __future__ import annotations

import json
import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import cache
from pathlib import Path
from typing import Any

from contract import Client

REPO = Path(__file__).resolve().parent.parent
IST = timezone(timedelta(hours=5, minutes=30))


# ---------------------------------------------------------------- scenario model


@dataclass(frozen=True)
class ReportStep:
    body: dict[str, Any]
    expect: frozenset[int] = frozenset({201})


@dataclass
class Outcome:
    """What the server said while the scenario's reports were posted."""

    statuses: list[int] = field(default_factory=list)
    replies: list[Any] = field(default_factory=list)
    challenge_statuses: list[int] = field(default_factory=list)


CheckFn = Callable[[Client, Outcome], None]


@dataclass(frozen=True)
class Check:
    """One expectation. `row` is the PRD scoring row it feeds: 1 to 7, or a bonus key."""

    row: str
    label: str
    fn: CheckFn


@dataclass
class Scenario:
    family: str
    seed: int
    salt: str
    variant: str
    reports: list[ReportStep] = field(default_factory=list)
    challenges: list[dict[str, Any]] = field(default_factory=list)
    reset_before_checks: bool = False
    checks: list[Check] = field(default_factory=list)

    def check(self, row: str, label: str) -> Callable[[CheckFn], CheckFn]:
        def register(fn: CheckFn) -> CheckFn:
            self.checks.append(Check(row, label, fn))
            return fn

        return register


@dataclass(frozen=True)
class Person:
    reporter_id: str
    ip_prefix: str


# ---------------------------------------------------------------- reference data


def _items(name: str) -> list[dict[str, Any]]:
    path = REPO / "shared" / "data" / f"{name}.json"
    items: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))["items"]
    return items


@cache
def areas() -> dict[str, dict[str, Any]]:
    return {str(a["pincode"]): a for a in _items("areas")}


@cache
def scam_types() -> list[str]:
    return [str(s["id"]) for s in _items("scam_types") if s["id"] != "other"]


@cache
def channels() -> list[str]:
    return [str(c["id"]) for c in _items("channels")]


@cache
def verified() -> list[dict[str, Any]]:
    return _items("verified")


def distance_km(a: str, b: str) -> float:
    """Great-circle distance between two areas' Appendix B points."""
    pa, pb = areas()[a], areas()[b]
    lat1, lng1, lat2, lng2 = map(math.radians, (pa["lat"], pa["lng"], pb["lat"], pb["lng"]))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def phone_formats(national: str) -> list[str]:
    """The PRD's spellings of one 10-digit number, plus a few of our own."""
    a, b = national[:5], national[5:]
    return [f"+91 {a} {b}", f"0{national}", f"{a}-{b}", f"91{national}", f"+91{national}"]


def jaccard(a: str, b: str, k: int = 3) -> float:
    """Character-shingle similarity, the measure the trust rules use for copied notes."""
    sa = {a[i : i + k] for i in range(max(len(a) - k + 1, 1))}
    sb = {b[i : i + k] for i in range(max(len(b) - k + 1, 1))}
    return len(sa & sb) / len(sa | sb) if sa | sb else 1.0


# ---------------------------------------------------------------- notes in people's own words
# English only for now; notes in Hindi and Hinglish are a later edge case.

_EN = {
    "open": [
        "Got a call this morning",
        "A man phoned me around lunch",
        "My father received a video call",
        "Someone called my wife yesterday",
        "I picked up an unknown number on the bus",
        "Late evening a woman rang",
        "While at the office a person called",
        "My neighbour aunty got this call",
        "Received a WhatsApp call from this ID",
        "My son forwarded me this, the caller",
        "Was cooking when the phone rang, the guy",
        "Just after my shift ended someone",
        "My grandmother got a call on her landline",
        "During a meeting an unknown caller",
        "On Sunday morning a man",
        "Right after I paid my electricity bill someone",
        "A few minutes after a missed call, a guy",
        "At the railway station a caller",
        "My college roommate's number was spoofed and the caller",
        "While driving I answered and the person",
        "An international looking number rang and the man",
        "My dad's old Nokia got a call where someone",
    ],
    "claim": [
        "said he was from the cyber police",
        "claimed to be a courier company officer",
        "pretended to be from the electricity board",
        "told me my bank KYC had expired",
        "said a parcel in my name had drugs",
        "offered a part time job liking videos",
        "said I won a lucky draw car",
        "said my loan was approved instantly",
        "claimed to be customer care of my bank",
        "said my SIM would be blocked in two hours",
        "asked me to scan a QR to get a refund",
        "said my son was arrested and needed bail",
        "said there was a warrant against my Aadhaar",
        "said my PAN card was linked to money laundering",
        "claimed my credit card had a suspicious transaction",
        "said I had to verify my gas connection",
        "offered crypto trading with guaranteed returns",
        "said my insurance policy had matured",
        "pretended to be from TRAI about my number",
        "claimed to be my cousin stuck abroad",
        "said a customs duty was pending on a gift",
        "said my FASTag was blacklisted",
    ],
    "ask": [
        "and asked for {amt} rupees",
        "and wanted the OTP that came to my phone",
        "and kept me on the line for {mins} minutes",
        "and asked me to install a screen sharing app",
        "and demanded a fine of {amt}",
        "and asked for my card number and CVV",
        "and told me not to tell anyone at home",
        "and shared a link to update details",
        "and asked me to transfer to a safe account",
        "and wanted me to buy gift cards",
        "and asked for my net banking password",
        "and told me to stay on video the whole time",
        "and asked me to pay a small registration fee first",
        "and wanted a photo of my debit card",
    ],
    "end": [
        "I cut the call.",
        "Luckily my daughter stopped me.",
        "I lost {amt} before I realised.",
        "I blocked the number after that.",
        "He got angry when I asked questions.",
        "I went to the bank branch to check, it was fake.",
        "Called 1930 afterwards.",
        "Very scary, please be careful everyone.",
        "Uniform and office background looked real.",
        "My friend in {place} got the same thing.",
        "Reported it on the portal the same day.",
        "My bank said they never call like this.",
        "I told everyone in the society WhatsApp group.",
        "Took screenshots of everything.",
        "Still shaking thinking about it.",
        "Hope nobody else falls for this.",
        "My husband handled the rest.",
    ],
    "detail": [
        "He knew my full name and address.",
        "There were sirens playing in the background.",
        "The caller ID showed {place}.",
        "He sent a photo of an ID card on WhatsApp.",
        "His English was very formal, like reading a script.",
        "Another man came on the line pretending to be his senior.",
        "He said not to cut the call or I would be arrested.",
        "The link looked exactly like the bank website.",
        "He spoke Hindi first then switched to English.",
        "They had my old phone number also.",
        "He said the case number was {mins}{amt}.",
        "It went on until my battery died.",
        "A lady confirmed the 'department' when I asked.",
        "The number had a profile picture of a police logo.",
        "He sent a fake court notice PDF.",
        "He read out my last transaction correctly.",
        "The SMS had spelling mistakes.",
        "He asked which bank I use before anything else.",
        "A second call came from a different number.",
        "He claimed the call was being recorded for evidence.",
        "He used a lot of legal words to scare me.",
        "He said my family would also be questioned.",
        "The website asked for my UPI PIN.",
        "He was shouting and very rude.",
    ],
}

_PLACES = ["Jayanagar", "Whitefield", "Pune", "Mysore", "Hebbal", "Delhi", "BTM", "Kochi"]
_PSPS = ["okaxis", "oksbi", "okhdfcbank", "okicici", "ybl", "paytm", "ibl", "axl"]
_TLDS = ["in", "com", "co.in", "online", "xyz", "info", "net"]
_WORDS = [
    "kyc",
    "update",
    "verify",
    "refund",
    "secure",
    "bank",
    "pay",
    "help",
    "care",
    "bonus",
    "reward",
    "parcel",
    "track",
    "power",
    "bill",
    "loan",
    "job",
    "task",
    "win",
    "claim",
]


def _style(rng: random.Random, text: str) -> str:
    """People write differently: some in lower case, some without punctuation, some briefly."""
    roll = rng.random()
    if roll < 0.25:
        text = text.lower()
    elif roll < 0.4:
        text = text.replace(".", "").replace(",", "")
    if rng.random() < 0.3:
        text = rng.choice(["pls beware ", "FYI ", "warning: ", "sharing so others know - "]) + text
    if rng.random() < 0.3:
        text += rng.choice([" !!", " :(", " plz share", " stay safe", " be careful"])
    return text


# ---------------------------------------------------------------- the generator


class Gen:
    """Everything random in a scenario comes from here, seeded by (family, seed, salt)."""

    def __init__(self, family: str, seed: int, salt: str, now: datetime) -> None:
        self.family = family
        self.seed = seed
        self.salt = salt
        self.now = now
        self.rng = random.Random(f"{family}:{seed}:{salt}")
        self._n = 0

    def scenario(self, variant: str) -> Scenario:
        return Scenario(self.family, self.seed, self.salt, variant)

    def _next(self) -> int:
        self._n += 1
        return self._n

    def _token(self, n: int = 8) -> str:
        return "".join(self.rng.choice("0123456789abcdef") for _ in range(n))

    # identifiers
    def mobile(self) -> str:
        return self.rng.choice("6789") + "".join(self.rng.choice("0123456789") for _ in range(9))

    def landline(self) -> str:
        """A Bengaluru landline, the kind a small business has (+91 80 ...)."""
        return (
            "80"
            + self.rng.choice("23456789")
            + "".join(self.rng.choice("0123456789") for _ in range(7))
        )

    def upi(self) -> str:
        name = self.rng.choice(["ravi", "priya", "shop", "store", "help", "refund", "pay"])
        return f"{name}{self.rng.randint(10, 99999)}@{self.rng.choice(_PSPS)}"

    def url(self) -> str:
        host = "-".join(self.rng.sample(_WORDS, 2)) + str(self.rng.randint(1, 999))
        return f"https://{host}.{self.rng.choice(_TLDS)}/{self.rng.choice(_WORDS)}"

    def sender(self) -> str:
        return "".join(self.rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(6))

    def identifier(self, kind: str | None = None) -> tuple[str, str, str]:
        """(type, value as a reporter would type it, the server's normalised form)."""
        kind = kind or self.rng.choice(["phone", "phone", "upi", "url", "sender_id"])
        if kind == "phone":
            n = self.mobile()
            return kind, self.rng.choice(phone_formats(n)), f"+91{n}"
        if kind == "upi":
            u = self.upi()
            return kind, self.rng.choice([u, u.upper(), u.capitalize()]), u
        if kind == "url":
            u = self.url()
            host_path = u.removeprefix("https://")
            return kind, self.rng.choice([u, f"http://www.{host_path}?utm=sms", f"{host_path}/"]), u
        code = self.sender()
        return kind, self.rng.choice([code, f"VM-{code}", f"ad-{code.lower()}"]), code

    def spellings(self, kind: str, normalised: str) -> list[str]:
        """Several ways people type the same identifier."""
        if kind == "phone":
            return phone_formats(normalised.removeprefix("+91"))
        if kind == "upi":
            return [normalised, normalised.upper(), f" {normalised.capitalize()} "]
        if kind == "url":
            host_path = normalised.removeprefix("https://")
            return [
                normalised,
                f"http://www.{host_path}?utm=sms",
                f"{host_path}/",
                f"{normalised}#x",
            ]
        return [normalised, f"VM-{normalised}", f"AD-{normalised}", f"jd-{normalised.lower()}"]

    # people
    def prefix(self) -> str:
        first = self.rng.choice([49, 103, 106, 110, 117, 122, 157, 182, 203, 223])
        return f"{first}.{self.rng.randint(0, 255)}.{self.rng.randint(0, 255)}"

    def person(self, prefix: str | None = None) -> Person:
        return Person(reporter_id=f"r_{self._token()}", ip_prefix=prefix or self.prefix())

    def people(self, n: int, prefix: str | None = None) -> list[Person]:
        return [self.person(prefix) for _ in range(n)]

    # words
    def note(self) -> str:
        """A report in someone's own words: different parts, details and order every time."""
        bank = _EN
        details = {
            "amt": f"{self.rng.randint(1, 99) * 500:,}",
            "mins": str(self.rng.randint(4, 190)),
            "place": self.rng.choice(_PLACES),
        }
        story = [self.rng.choice(bank["open"]), self.rng.choice(bank["claim"])]
        if self.rng.random() < 0.7:
            story.append(self.rng.choice(bank["ask"]))
        extras = self.rng.sample(bank["detail"], self.rng.randint(1, 3))
        extras += self.rng.sample(bank["end"], self.rng.randint(1, 2))
        self.rng.shuffle(extras)
        text = " ".join(story) + ". " + " ".join(extras)
        if self.rng.random() < 0.4:
            hour = self.rng.randint(7, 22)
            text += f" around {hour}:{self.rng.randint(0, 59):02d}"
        return _style(self.rng, text.format(**details))

    # places and times
    def area(self, city: str | None = "Bengaluru") -> str:
        pins = [p for p, a in areas().items() if city is None or a["city"] == city]
        return self.rng.choice(sorted(pins))

    def ago(self, **delta: float) -> datetime:
        return self.now - timedelta(**delta)

    # reports
    def report(
        self,
        person: Person,
        kind: str,
        value: str,
        *,
        occurred: datetime,
        pincode: str | None = None,
        note: str | None = None,
        scam_type: str | None = None,
        channel: str | None = None,
        delay_minutes: float | None = None,
        expect: frozenset[int] = frozenset({201}),
    ) -> ReportStep:
        """A PRD Appendix A report. reported_at follows occurred_at by minutes to hours."""
        delay = delay_minutes if delay_minutes is not None else self.rng.uniform(3, 240)
        reported = min(occurred + timedelta(minutes=delay), self.now)
        pin = pincode or self.area()
        area = areas()[pin]
        body = {
            "report_id": f"rep_{self.family}_{self.seed}_{self._token(6)}_{self._next()}",
            "occurred_at": occurred.astimezone(IST).replace(microsecond=0).isoformat(),
            "reported_at": reported.astimezone(IST).replace(microsecond=0).isoformat(),
            "reporter_id": person.reporter_id,
            "ip_prefix": person.ip_prefix,
            "channel": channel or self.rng.choice(channels()),
            "scam_type": scam_type or self.rng.choice(scam_types()),
            "identifier_type": kind,
            "identifier_value": value,
            "pincode": pin,
            "locality": area["locality"],
            "city": area["city"],
            "note": note if note is not None else self.note(),
            "has_screenshot": self.rng.random() < 0.3,
            "amount_lost_inr": self.rng.choice([0, 0, 0, 500, 2000, 15000, 200000]),
        }
        return ReportStep(body, expect)


# ---------------------------------------------------------------- reading the server


def lookup(client: Client, kind: str, value: str) -> dict[str, Any]:
    response = client.get("/lookup", params={"type": kind, "value": value})
    if response.status_code != 200:
        raise AssertionError(f"lookup {kind} was {response.status_code}, want 200")
    body: dict[str, Any] = response.json()
    return body


def area_map(client: Client, pincode: str, **params: float) -> list[dict[str, Any]]:
    query = {"pincode": pincode} | {k: str(v) for k, v in params.items()}
    response = client.get("/map", params=query)
    if response.status_code != 200:
        raise AssertionError(f"map was {response.status_code}, want 200")
    clusters: list[dict[str, Any]] = response.json()["clusters"]
    return clusters


def alerts(client: Client, pincode: str) -> list[dict[str, Any]]:
    response = client.get("/alerts", params={"pincode": pincode})
    if response.status_code != 200:
        raise AssertionError(f"alerts was {response.status_code}, want 200")
    found: list[dict[str, Any]] = response.json()["alerts"]
    return found


def masked_like(kind: str, normalised: str) -> str:
    """The PRD's masked display_value for fewer than 3 reporters."""
    if kind == "phone":
        d = normalised.removeprefix("+91")
        return f"{d[:2]}XXXXX{d[-3:]}"
    if kind == "upi":
        handle, _, psp = normalised.partition("@")
        return f"{handle[:1]}***@{psp}"
    if kind == "url":
        host = normalised.removeprefix("https://").split("/", 1)[0].split(".")
        return f"{host[0][:3]}***.{host[-1]}/..."
    return f"{normalised[:2]}****"
