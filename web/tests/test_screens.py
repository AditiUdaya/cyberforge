"""Every screen, against a fake API, in English, Hindi and icon-only mode (SPEC test layer 8).

Owner: A. Filled in by: A5.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from scam_web.i18n import STRINGS
from tests.fake_api import FakeApi

PAGE = str(Path(__file__).resolve().parents[1] / "scam_web" / "pages" / "{}.py")
PRD_MESSAGE = (
    "Your KYC has expired. Update now at http://www.sbi-kyc.in/pay?utm=sms or call +91 98765 43210"
)


def screen(name: str, api: FakeApi, **state: Any) -> AppTest:
    at = AppTest.from_file(PAGE.format(name), default_timeout=20)
    at.session_state["api_client"] = api
    for key, value in state.items():
        at.session_state[key] = value
    return at.run()


def text_of(at: AppTest) -> str:
    parts = [m.value for m in at.markdown] + [m.value for m in at.caption]
    for kind in (at.error, at.warning, at.info, at.success):
        parts += [str(m.value) for m in kind]
    return "\n".join(str(p) for p in parts)


def click(at: AppTest, contains: str) -> AppTest:
    for button in at.button:
        if contains in str(button.label):
            return button.click().run()
    raise AssertionError(f"no button containing {contains!r}: {[b.label for b in at.button]}")


@pytest.mark.parametrize("name", ["check", "report", "map", "challenge", "licence", "how"])
@pytest.mark.parametrize("lang", ["en", "hi"])
@pytest.mark.parametrize("icons", [False, True])
def test_every_screen_renders_cleanly(name: str, lang: str, icons: bool) -> None:
    at = screen(name, FakeApi(), lang=lang, icons_only=icons)
    assert not at.exception, at.exception


def test_check_finds_every_identifier_in_a_pasted_message() -> None:
    at = screen("check", FakeApi(), check_text=PRD_MESSAGE)
    at = click(at, "Check")
    text = text_of(at)
    assert "Known scam" in text
    assert "Reported by 7 people near you" in text
    assert "No reports" in text
    assert "does not mean it is safe" in text
    # Shown literally: the asterisks are escaped, so Markdown does not turn them into bold.
    assert r"sbi\*\*\*\.in/\.\.\." in text
    assert "HSR Layout" in text
    assert not at.exception


def test_check_in_hindi() -> None:
    at = screen("check", FakeApi(), lang="hi", check_text="+91 98765 43210")
    at = click(at, STRINGS["check_button"]["hi"])
    assert "आपके आस-पास 7 लोगों ने रिपोर्ट किया" in text_of(at)


def test_check_with_nothing_found_says_so() -> None:
    at = click(screen("check", FakeApi(), check_text="hello 12345"), "Check")
    assert "No phone number" in text_of(at)


def test_expired_licence_shows_the_prd_message() -> None:
    at = click(screen("check", FakeApi(expired=True), check_text="+91 98765 43210"), "Check")
    assert "Licence expired. Contact your provider." in text_of(at)
    assert not at.exception


def fill_report(**changes: Any) -> dict[str, Any]:
    return {
        "report_channel": "Phone call",
        "report_scam_type": "digital-arrest",
        "report_area": "HSR Layout, Bengaluru",
        "report_value": "+91 98765 43210",
        "report_note": "Man in police uniform on a video call asked for money.",
    } | changes


def test_report_sends_a_prd_body_without_login() -> None:
    api = FakeApi()
    at = click(screen("report", api, **fill_report()), "Send report")
    assert "Thank you" in text_of(at)
    [body] = api.reports
    required = {
        "report_id",
        "occurred_at",
        "reported_at",
        "reporter_id",
        "channel",
        "scam_type",
        "identifier_type",
        "identifier_value",
        "pincode",
    }
    assert required <= body.keys()
    assert "ip_prefix" not in body
    assert body["identifier_type"] == "phone"
    assert (body["pincode"], body["locality"]) == ("560102", "HSR Layout")
    occurred = datetime.fromisoformat(body["occurred_at"])
    assert occurred.utcoffset() == timedelta(hours=5, minutes=30)
    assert body["reporter_id"].startswith("d_")


def test_report_remembers_the_area_and_keeps_the_device_id() -> None:
    api = FakeApi()
    at = click(screen("report", api, **fill_report()), "Send report")
    assert at.session_state["my_area"] == "HSR Layout, Bengaluru"
    at.session_state["report_value"] = "ravi12@okaxis"
    click(at, "Send report")
    assert api.reports[0]["reporter_id"] == api.reports[1]["reporter_id"]


def test_report_needs_channel_type_and_area() -> None:
    api = FakeApi()
    at = click(screen("report", api, **fill_report(report_channel=None)), "Send report")
    assert "Please choose" in text_of(at)
    assert api.reports == []


def test_report_rejects_junk_before_sending() -> None:
    api = FakeApi()
    at = click(screen("report", api, **fill_report(report_value="12345")), "Send report")
    assert "does not look like" in text_of(at)
    assert api.reports == []


def test_report_429_asks_to_wait() -> None:
    at = click(screen("report", FakeApi(report_status=429), **fill_report()), "Send report")
    assert "try again in an hour" in text_of(at)


def test_report_works_with_icons_only() -> None:
    api = FakeApi()
    at = screen("report", api, icons_only=True, **fill_report())
    labels = [str(b.label) for b in at.button]
    assert "📣" in labels
    click(at, "📣")
    assert len(api.reports) == 1


def test_got_this_too_prefills_the_report() -> None:
    at = screen("report", FakeApi(), prefill="+91 98765 43210")
    assert at.session_state["report_value"] == "+91 98765 43210"


def test_map_lists_clusters_and_alerts() -> None:
    api = FakeApi()
    api.clusters = [
        {
            "pincode": "560102",
            "locality": "HSR Layout",
            "city": "Bengaluru",
            "count": 12,
            "top_scam_type": "digital-arrest",
            "severity": "CRIT",
            "lat": 12.9116,
            "lng": 77.6473,
        },
    ]
    api.found_alerts = [
        {
            "type": "SPIKE",
            "pincode": "560102",
            "window": "24h",
            "count": 10,
            "baseline_per_day": 2.0,
        },
        {"type": "NEW_TYPE", "pincode": "560102", "scam_type": "job-offer", "window": "24h"},
    ]
    text = text_of(screen("map", api))
    assert "HSR Layout" in text and "12 reports" in text
    assert "10 in 24 hours" in text
    assert "A new kind of scam near you" in text


def test_map_without_reports_is_calm() -> None:
    text = text_of(screen("map", FakeApi()))
    assert "No reports near here" in text
    assert "No alerts" in text


def test_challenge_sends_the_prd_fields() -> None:
    api = FakeApi()
    at = screen("challenge", api)
    at.text_input[0].input("+91 80 4100 2233")
    at.text_input[1].input("Fresh Bakes")
    at.text_input[2].input("owner@example.com")
    at.text_area[0].input("GST certificate attached.")
    at = click(at, "Send for review")
    assert api.challenges == [
        {
            "identifier_type": "phone",
            "identifier_value": "+91 80 4100 2233",
            "claimant_name": "Fresh Bakes",
            "contact_email": "owner@example.com",
            "proof_note": "GST certificate attached.",
        }
    ]
    assert "under review" in text_of(at)


def test_licence_screen_shows_who_and_until_when() -> None:
    text = text_of(screen("licence", FakeApi()))
    assert "Demo Bank" in text and "Licence is valid" in text


def test_licence_screen_works_when_expired() -> None:
    api = FakeApi(expired=True)
    api.licence_body = {
        "licensee": "Demo Bank",
        "expires_at": "2026-10-31T10:05:00+05:30",
        "valid": False,
    }
    at = screen("licence", api)
    assert "Licence expired. Contact your provider." in text_of(at)
    assert not at.exception


def test_shortcuts_reach_the_main_screens() -> None:
    at = screen("map", FakeApi())
    labels = [str(b.label) for b in at.button]
    assert any("Check" in x for x in labels) and any("Report" in x for x in labels)
    assert not any(x.endswith("Map") for x in labels)


def test_language_and_icon_mode_survive_a_page_change() -> None:
    # After a page change the switches come back with stale values; the lasting choice wins.
    at = screen(
        "check", FakeApi(), lang="hi", icons_only=True, _lang_switch="en", _icons_switch=False
    )
    assert at.session_state["lang"] == "hi"
    assert at.session_state["icons_only"] is True
    assert "🔍" in [str(b.label) for b in at.button]
    assert not at.exception


def test_icon_switch_writes_back_to_the_lasting_choice() -> None:
    at = screen("check", FakeApi())
    at = at.toggle[0].set_value(True).run()
    assert at.session_state["icons_only"] is True
