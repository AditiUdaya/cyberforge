"""Turns phone, UPI, URL and sender_id values into their single standard form.
Rules in ARCHITECTURE.md 'Normalisation rules'; cases in shared/vectors/normalise.json.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations

import re
from typing import Literal

from app.shared_data import data_items

IdentifierType = Literal["phone", "upi", "url", "sender_id"]


class InvalidIdentifier(ValueError):
    """The value cannot be a valid identifier of its type; the API replies 400."""


_PHONE_CHARS = re.compile(r"^[0-9+\-.() ]+$")
_TOLL_FREE = ("1800", "1860")
_TOLL_FREE_REST = range(4, 8)
_UPI = re.compile(r"^[a-z0-9._-]{2,256}@[a-z][a-z0-9]{1,63}$")
_HOST = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,63}$")
_SENDER = re.compile(r"^(?:[A-Z]{2}-)?([A-Z]{6})(?:-[A-Z])?$")


def normalise(kind: IdentifierType, raw: str) -> str:
    if kind == "phone":
        return _phone(raw)
    if kind == "upi":
        return _upi(raw)
    if kind == "url":
        return _url(raw)
    return _sender(raw)


def _short_codes() -> frozenset[str]:
    return frozenset(str(item["value"]) for item in data_items("short_codes"))


def _phone(raw: str) -> str:
    text = raw.strip()
    if not text or not _PHONE_CHARS.match(text):
        raise InvalidIdentifier("phone")
    bare = text.replace("(", "").replace(")", "").strip()
    has_plus = bare.startswith("+")
    if "+" in bare[1:]:
        raise InvalidIdentifier("phone")
    digits = "".join(ch for ch in bare if ch.isdigit())

    if has_plus:
        if not digits.startswith("91"):
            raise InvalidIdentifier("phone")
        return _indian(digits[2:])
    if digits in _short_codes():
        return digits
    if digits.startswith(_TOLL_FREE):
        if len(digits) - 4 in _TOLL_FREE_REST:
            return digits
        raise InvalidIdentifier("phone")
    if digits.startswith("0091"):
        return _indian(digits[4:])
    if len(digits) == 12 and digits.startswith("91"):
        return _indian(digits[2:])
    if len(digits) == 11 and digits.startswith("0"):
        return _indian(digits[1:])
    return _indian(digits)


def _indian(national: str) -> str:
    if len(national) != 10 or national[0] not in "23456789":
        raise InvalidIdentifier("phone")
    return f"+91{national}"


def _upi(raw: str) -> str:
    value = "".join(raw.split()).lower()
    if not _UPI.match(value):
        raise InvalidIdentifier("upi")
    return value


def _url(raw: str) -> str:
    text = raw.strip()
    if not text or any(ch.isspace() for ch in text):
        raise InvalidIdentifier("url")
    if "://" in text:
        scheme, _, rest = text.partition("://")
        if scheme.lower() not in ("http", "https"):
            raise InvalidIdentifier("url")
    else:
        rest = text
    for cut in ("?", "#"):
        rest = rest.split(cut, 1)[0]
    host, slash, path = rest.partition("/")
    host = host.lower()
    if host.startswith("www.") and "." in host[4:]:
        host = host[4:]
    if not _HOST.match(host):
        raise InvalidIdentifier("url")
    path = (slash + path).rstrip("/")
    return f"https://{host}{path}"


def _sender(raw: str) -> str:
    match = _SENDER.match(raw.strip().upper())
    if match is None:
        raise InvalidIdentifier("sender_id")
    return match.group(1)
