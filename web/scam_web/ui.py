"""Shared screen pieces: language and icon switches, the API handle, the expired screen,
the anonymous device id, and the verdict card.

Owner: A. Filled in by: A1.
"""

from __future__ import annotations

import re
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, cast

import streamlit as st

from scam_web.api_client import Api, ApiError, HttpApi, LicenceExpired
from scam_web.i18n import (
    LANGS,
    PAGE_ICONS,
    VERDICT_ICONS,
    Lang,
    channel_label,
    scam_label,
    t,
)

PAGES = {
    "check": "scam_web/pages/check.py",
    "report": "scam_web/pages/report.py",
    "map": "scam_web/pages/map.py",
    "challenge": "scam_web/pages/challenge.py",
    "licence": "scam_web/pages/licence.py",
    "how": "scam_web/pages/how.py",
}


def lang() -> Lang:
    return cast(Lang, st.session_state.get("lang") or "en")


def icons_only() -> bool:
    return bool(st.session_state.get("icons_only", False))


def tr(key: str, **values: object) -> str:
    return t(key, lang(), **values)


def label(icon: str, text: str) -> str:
    """Icon and words, or the icon alone in icon-only mode."""
    return icon if icons_only() else f"{icon} {text}"


_MARKDOWN = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~])")


def md(text: object) -> str:
    """Values from the API shown literally: a masked r***@okaxis must not turn into bold."""
    return _MARKDOWN.sub(r"\\\1", str(text))


SHORTCUTS = ("check", "report", "map")


def header(page: str) -> None:
    """Title, shortcuts to the main screens, and the language and icon-only switches.

    On a phone Streamlit folds the page menu away, so the three screens people need most
    are always one tap away here.
    """
    # The choices live in plain keys. Streamlit drops a widget's own key when the next page does
    # not draw that widget, so each switch gets a copy before drawing and writes back on change.
    if not st.session_state.get("lang"):
        st.session_state["lang"] = "en"
    st.session_state["_lang_switch"] = st.session_state["lang"]
    st.session_state["_icons_switch"] = icons_only()
    links = st.columns(len(SHORTCUTS))
    for column, name in zip(links, SHORTCUTS, strict=True):
        if name != page and column.button(
            label(PAGE_ICONS[name], tr("nav_" + name)), key=f"go_{name}", use_container_width=True
        ):
            st.switch_page(PAGES[name])
    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"### {PAGE_ICONS[page]} {tr('nav_' + page)}")
    with right:
        st.segmented_control(
            "language",
            options=list(LANGS),
            format_func=lambda code: LANGS[code],
            key="_lang_switch",
            on_change=_keep_choices,
            label_visibility="collapsed",
        )
        st.toggle(f"🖼️ {tr('icons_only')}", key="_icons_switch", on_change=_keep_choices)


def _keep_choices() -> None:
    if st.session_state.get("_lang_switch"):
        st.session_state["lang"] = st.session_state["_lang_switch"]
    st.session_state["icons_only"] = bool(st.session_state.get("_icons_switch"))


def api() -> Api:
    injected = st.session_state.get("api_client")
    if injected is not None:
        return cast(Api, injected)
    return _http_api()


@st.cache_resource
def _http_api() -> HttpApi:
    return HttpApi()


@contextmanager
def guarded() -> Iterator[None]:
    """Turn the API's expired-licence and network errors into the right screen."""
    try:
        yield
    except LicenceExpired:
        st.error(f"🔒 {tr('expired')}")
        st.stop()
    except ApiError as e:
        if e.status == 0:
            st.warning(f"📡 {tr('unreachable')}")
            st.stop()
        raise


def device_id() -> str:
    """A random, anonymous id for this browser session, sent as reporter_id. Linked to nothing."""
    if "device_id" not in st.session_state:
        st.session_state["device_id"] = f"d_{secrets.token_hex(8)}"
    return str(st.session_state["device_id"])


def areas() -> list[dict[str, Any]]:
    if "areas" not in st.session_state:
        with guarded():
            st.session_state["areas"] = api().areas()
    found: list[dict[str, Any]] = st.session_state["areas"]
    return found


def area_name(area: dict[str, Any]) -> str:
    return f"{area['locality']}, {area['city']}"


def short_date(iso: str | None) -> str:
    if not iso:
        return "-"
    return datetime.fromisoformat(iso).strftime("%d %b %Y, %H:%M")


def verdict_card(kind: str, value: str, result: dict[str, Any]) -> None:
    verdict = str(result["verdict"])
    people = int(result["distinct_reporters"])
    with st.container(border=True):
        st.markdown(f"## {VERDICT_ICONS[verdict]} {tr('verdict_' + verdict)}")
        st.markdown(f"**{md(result['display_value'])}**")
        if verdict == "VERIFIED_BUSINESS":
            st.success(tr("verified_note"))
        elif people == 0:
            st.info(tr("no_reports_note"))
        else:
            st.markdown(tr("reported_by_one") if people == 1 else tr("reported_by", n=people))
            st.caption(
                tr(
                    "seen_between",
                    first=short_date(result.get("first_seen")),
                    last=short_date(result.get("last_seen")),
                )
            )
        if result.get("challenged"):
            st.warning(f"🏪 {tr('challenged_badge')}")
        evidence = result.get("evidence") or []
        if evidence and verdict != "VERIFIED_BUSINESS":
            st.markdown(f"**{tr('recent_reports')}**")
            for item in evidence:
                when = short_date(item["occurred_at"])
                how = channel_label(item["channel"], lang())
                what = scam_label(item["scam_type"], lang())
                where = _area_label(item["pincode"])
                st.markdown(f"- {md(when)} · {md(how)} · {md(what)} · {md(where)}")
        cols = st.columns(3)
        if verdict != "VERIFIED_BUSINESS" and cols[0].button(
            label("📣", tr("got_this_too")), key=f"same_{kind}_{value}"
        ):
            st.session_state["prefill"] = value
            st.switch_page(PAGES["report"])
        cols[1].link_button(label("📞", tr("call_1930")), "tel:1930")
        cols[2].link_button(label("🛡️", tr("report_portal")), "https://cybercrime.gov.in")


def _area_label(pincode: str) -> str:
    for area in st.session_state.get("areas", []):
        if area["pincode"] == pincode:
            return str(area["locality"])
    return pincode
