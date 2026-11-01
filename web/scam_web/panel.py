"""The right-hand live panel on every screen: live alerts, then everything that happened.

Refreshes itself every few seconds without reloading the page. Reports counted, repeats merged,
coordinated bursts, junk rejected, reporters slowed down, new known scams, disputes and alerts
all appear here. Numbers are always masked and no reporter detail ever appears.

Owner: A. Filled in by: A4.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from scam_web.api_client import ApiError, LicenceExpired
from scam_web.i18n import CHANNEL_ICONS, SCAM_ICONS, STRINGS, channel_label, scam_label
from scam_web.ui import api, header, lang, md, tr

REFRESH_SECONDS = 3
ICONS = {
    "report": "✅",
    "merged": "🔁",
    "burst": "🚩",
    "rejected": "⛔",
    "rate_limited": "⏳",
    "known_scam": "🔴",
    "dispute": "🏪",
    "alert": "🔔",
}


def _clock(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%H:%M:%S")


def alert_line(alert: dict[str, Any]) -> str:
    area = alert.get("locality") or alert["pincode"]
    if alert["type"] == "SPIKE":
        text = tr(
            "alert_spike_short", area=area, count=alert["count"], base=alert["baseline_per_day"]
        )
        return f"📈 {md(text)}"
    kind = scam_label(str(alert.get("scam_type")), lang())
    return f"🆕 {md(tr('alert_new_short', area=area, kind=kind))}"


def event_line(event: dict[str, Any]) -> str:
    kind = event["kind"]
    count = int(event["count"])
    if kind == "burst":
        title = tr("ev_burst", count=count)
    elif kind == "rejected":
        reason = str(event.get("detail"))
        key = f"reason_{reason}"
        title = tr("ev_rejected", reason=tr(key) if key in STRINGS else reason)
    else:
        title = tr(f"ev_{kind}")
    if count > 1 and kind != "burst":
        title += f" ({count})"

    parts: list[str] = []
    if kind == "alert":
        if event.get("detail") == "SPIKE":
            parts.append(f"📈 {tr('kind_spike')}")
        elif event.get("scam_type"):
            parts.append(f"🆕 {scam_label(str(event['scam_type']), lang())}")
    if event.get("channel"):
        icon = CHANNEL_ICONS.get(str(event["channel"]), "❓")
        parts.append(f"{icon} {channel_label(str(event['channel']), lang())}")
    if event.get("scam_type") and kind != "alert":
        icon = SCAM_ICONS.get(str(event["scam_type"]), "❓")
        parts.append(f"{icon} {scam_label(str(event['scam_type']), lang())}")
    if event.get("locality"):
        parts.append(f"📍 {event['locality']}")
    if event.get("display"):
        parts.append(str(event["display"]))
    parts.append(_clock(event["at"]))
    detail = " · ".join(md(p) for p in parts)
    return f"{ICONS.get(kind, '•')} **{md(title)}**  \n{detail}"


@st.fragment(run_every=REFRESH_SECONDS)
def live_panel() -> None:
    """Drawn in the right-hand column of every screen; re-runs on its own every few seconds."""
    st.markdown(f"#### 🔔 {tr('panel_alerts')}")
    try:
        feed = api().activity()
    except LicenceExpired:
        st.error(f"🔒 {tr('expired')}")
        return
    except ApiError:
        st.caption(f"📡 {tr('unreachable')}")
        return

    if feed["alerts"]:
        for alert in feed["alerts"]:
            st.warning(alert_line(alert))
    else:
        st.caption(tr("panel_no_alerts"))

    st.markdown(f"#### 🧾 {tr('panel_activity')}")
    with st.container(height=520, border=False):
        if not feed["events"]:
            st.caption(tr("panel_quiet"))
        for event in feed["events"]:
            st.markdown(event_line(event))
    st.caption(f"🔒 {tr('panel_privacy')}")


def page(name: str) -> DeltaGenerator:
    """Lay out a screen: its content on the left, the live panel on the right.

    Returns the left column for the screen to draw into. On a phone the columns stack, so the
    panel follows the screen's content.
    """
    main, side = st.columns([5, 3], gap="large")
    with side:
        live_panel()
    with main:
        header(name)
    return main
