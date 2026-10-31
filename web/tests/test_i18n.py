"""Both languages complete, every option has an icon, and no banned words anywhere (A3).

Owner: A. Filled in by: A3.
"""

from __future__ import annotations

import re

from scam_web.i18n import (
    BANNED_WORDS,
    CHANNEL_HI,
    CHANNEL_ICONS,
    SCAM_EN,
    SCAM_HI,
    SCAM_ICONS,
    STRINGS,
)
from scam_web.shared import channel_ids, scam_type_ids


def every_shown_string() -> list[str]:
    shown = [text for both in STRINGS.values() for text in both.values()]
    return shown + list(CHANNEL_HI.values()) + list(SCAM_EN.values()) + list(SCAM_HI.values())


def test_every_string_exists_in_both_languages() -> None:
    for key, both in STRINGS.items():
        assert set(both) == {"en", "hi"}, key
        assert all(text.strip() for text in both.values()), key


def test_placeholders_match_across_languages() -> None:
    for key, both in STRINGS.items():
        assert set(re.findall(r"\{(\w+)\}", both["en"])) == set(
            re.findall(r"\{(\w+)\}", both["hi"])
        ), key


def test_every_channel_and_scam_type_has_icon_and_both_labels() -> None:
    for channel in channel_ids():
        assert channel in CHANNEL_ICONS and channel in CHANNEL_HI
    for scam_type in scam_type_ids():
        assert scam_type in SCAM_ICONS and scam_type in SCAM_EN and scam_type in SCAM_HI


def test_no_banned_words_in_either_language() -> None:
    for text in every_shown_string():
        lowered = text.lower()
        for word in BANNED_WORDS:
            assert word not in lowered, (word, text)


def test_prd_wording_is_used() -> None:
    assert STRINGS["reported_by"]["en"] == "Reported by {n} people near you"
    assert STRINGS["expired"]["en"] == "Licence expired. Contact your provider."
