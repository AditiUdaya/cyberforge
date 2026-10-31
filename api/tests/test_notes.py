"""Note fingerprints: copies match, light edits match, different words do not,
and the text cannot be recovered.

Owner: B. Filled in by: B5.
"""

from __future__ import annotations

from app.core.notes import similarity, sketch
from app.core.trust_config import NOTE_DUPLICATE_SIMILARITY

KEY = b"k" * 32
STORY = (
    "Got a call this morning, the man said he was from the cyber police and that a parcel "
    "in my name had drugs. He kept me on the line for forty minutes and asked for 25,000."
)


def test_identical_notes_are_duplicates() -> None:
    assert similarity(sketch(STORY, KEY), sketch(STORY, KEY)) == 1.0


def test_case_spacing_and_punctuation_do_not_hide_a_copy() -> None:
    shouted = STORY.upper().replace(",", "").replace(".", " !! ")
    assert similarity(sketch(STORY, KEY), sketch(shouted, KEY)) >= NOTE_DUPLICATE_SIMILARITY


def test_a_light_edit_is_still_a_duplicate() -> None:
    edited = STORY.replace("forty", "fifty") + " pls share"
    assert similarity(sketch(STORY, KEY), sketch(edited, KEY)) >= NOTE_DUPLICATE_SIMILARITY


def test_different_people_in_their_own_words_are_not_duplicates() -> None:
    other = (
        "My father picked up a video call. A man in uniform said his Aadhaar was used for money "
        "laundering and he would be arrested unless he paid a fine. We cut the call and blocked it."
    )
    assert similarity(sketch(STORY, KEY), sketch(other, KEY)) < 0.3


def test_short_or_empty_notes_have_no_fingerprint() -> None:
    assert sketch("", KEY) == b""
    assert sketch("scam call", KEY) == b""
    assert similarity(b"", b"") == 0.0
    assert similarity(sketch(STORY, KEY), b"") == 0.0


def test_fingerprint_is_keyed_and_holds_no_text() -> None:
    a, b = sketch(STORY, KEY), sketch(STORY, b"x" * 32)
    assert a != b
    assert similarity(a, b) < 0.1
    for word in (b"police", b"parcel", b"call", b"drugs"):
        assert word not in a
