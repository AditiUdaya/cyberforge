"""The right-hand live panel: alerts and every kind of event, masked, in both languages.

Owner: A. Filled in by: A5.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from scam_web.panel import event_line
from tests.fake_api import EVENTS, FakeApi

PAGES = Path(__file__).resolve().parents[1] / "scam_web" / "pages"


def screen(name: str, api: FakeApi, **state: Any) -> AppTest:
    at = AppTest.from_file(str(PAGES / f"{name}.py"), default_timeout=20)
    at.session_state["api_client"] = api
    for key, value in state.items():
        at.session_state[key] = value
    return at.run()


def shown(at: AppTest) -> str:
    parts = [m.value for m in at.markdown] + [m.value for m in at.caption]
    for kind in (at.error, at.warning, at.info, at.success):
        parts += [str(m.value) for m in kind]
    # As displayed: Markdown escapes such as \( are shown without the backslash.
    return "\n".join(str(p) for p in parts).replace("\\", "")


@pytest.mark.parametrize("name", ["check", "report", "map", "challenge", "licence", "how"])
def test_every_screen_has_the_live_panel(name: str) -> None:
    text = shown(screen(name, FakeApi()))
    assert "Live alerts" in text and "Activity" in text
    assert "Koramangala: 11 reports in 24 hours" in text


def test_every_event_kind_is_shown() -> None:
    text = shown(screen("how", FakeApi()))
    for words in [
        "Report counted",
        "Coordinated burst: 40 reports counted as one person",
        "Repeat from the same person or connection, counted once (2)",
        "Junk report rejected: not a valid phone number (3)",
        "Reporter slowed down",
        "Now a known scam",
        "Dispute filed",
        "Alert raised",
    ]:
        assert words in text, words


def test_masked_values_are_shown_literally() -> None:
    line = event_line(EVENTS[2])
    assert r"r\*\*\*@okaxis" in line


def test_the_panel_speaks_hindi() -> None:
    text = shown(screen("how", FakeApi(), lang="hi"))
    assert "ताज़ा चेतावनी" in text and "रिपोर्ट गिनी गई" in text


def test_an_empty_feed_says_so() -> None:
    api = FakeApi()
    api.events, api.live_alerts = [], []
    text = shown(screen("how", api))
    assert "No alerts right now." in text and "Nothing yet." in text


def test_expired_licence_shows_in_the_panel_too() -> None:
    text = shown(screen("how", FakeApi(expired=True)))
    assert "Licence expired. Contact your provider." in text


def test_no_reporter_detail_can_appear() -> None:
    for e in EVENTS:
        assert not {"reporter_id", "ip_prefix", "note"} & set(e)


def test_a_new_type_alert_says_reported_suspicious_activity() -> None:
    api = FakeApi()
    api.live_alerts = [
        {
            "type": "NEW_TYPE",
            "pincode": "560037",
            "scam_type": "fake-kyc-link",
            "window": "24h",
            "locality": "Marathahalli",
        },
    ]
    text = shown(screen("how", api))
    assert "Marathahalli: reported suspicious activity, Fake KYC link" in text
    assert "new kind of scam" not in text.lower()


def test_hindi_new_type_alert() -> None:
    api = FakeApi()
    api.live_alerts = [
        {
            "type": "NEW_TYPE",
            "pincode": "560037",
            "scam_type": "fake-kyc-link",
            "window": "24h",
            "locality": "Marathahalli",
        },
    ]
    assert "संदिग्ध गतिविधि की रिपोर्ट" in shown(screen("how", api, lang="hi"))
