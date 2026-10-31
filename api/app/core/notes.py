"""Note fingerprints: keyed bottom-k MinHash sketches of character shingles.

A sketch keeps only the NOTE_SKETCH_SIZE smallest keyed hashes of the note's 5-character
pieces, so it can tell copies apart from people's own words but cannot be turned back into
text. Characters, not words, so English, Hindi and Hinglish all work the same way.

Owner: B. Filled in by: B5.
"""

from __future__ import annotations

import hashlib
import re
import struct

from app.core.trust_config import NOTE_SHINGLE_CHARS, NOTE_SKETCH_SIZE, OWN_WORDS_MIN_CHARS

_NOT_WORD = re.compile(r"[\W_]+")
_HASH = struct.Struct(">Q")


def normalise_note(text: str) -> str:
    """Lower case, punctuation dropped, spacing collapsed: copies stay copies after restyling."""
    return " ".join(_NOT_WORD.sub(" ", text.lower()).split())


def sketch(text: str, key: bytes) -> bytes:
    """The fingerprint stored instead of the note. Empty for empty or very short notes."""
    if len(text.strip()) < OWN_WORDS_MIN_CHARS:
        return b""
    clean = normalise_note(text)
    k = NOTE_SHINGLE_CHARS
    pieces = {clean[i : i + k] for i in range(max(len(clean) - k + 1, 1))}
    hashes = sorted(
        {
            _HASH.unpack(hashlib.blake2b(p.encode(), key=key, digest_size=8).digest())[0]
            for p in pieces
        }
    )[:NOTE_SKETCH_SIZE]
    return b"".join(_HASH.pack(h) for h in hashes)


def _values(blob: bytes) -> set[int]:
    return {_HASH.unpack_from(blob, i)[0] for i in range(0, len(blob), _HASH.size)}


def similarity(a: bytes, b: bytes) -> float:
    """Estimated Jaccard similarity of the two notes' shingle sets (0 when either is empty)."""
    if not a or not b:
        return 0.0
    sa, sb = _values(a), _values(b)
    union = sorted(sa | sb)[:NOTE_SKETCH_SIZE]
    both = sum(1 for h in union if h in sa and h in sb)
    return both / len(union)
