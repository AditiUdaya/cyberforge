"""Report screen, icon first: channel, when, the identifier, scam type, area. One screen, no login.

Builds the PRD Appendix A report body: times in +05:30, a random device id as reporter_id, no
ip_prefix (the server takes the connection's prefix and keeps only its keyed hash).

Owner: A. Filled in by: A2.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone

import streamlit as st

from scam_web.api_client import ApiError
from scam_web.extract import detect
from scam_web.i18n import CHANNEL_ICONS, SCAM_ICONS, WHEN_ICONS, channel_label, scam_label
from scam_web.shared import channel_ids, scam_type_ids
from scam_web.ui import api, area_name, areas, device_id, guarded, header, label, lang, tr

IST = timezone(timedelta(hours=5, minutes=30))


def occurred_at(choice: str, picked_day: date | None, picked_time: time | None) -> datetime:
    now = datetime.now(IST)
    if choice == "today":
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return max(midnight, now - timedelta(hours=3))
    if choice == "yesterday":
        return now - timedelta(days=1)
    if choice == "pick" and picked_day is not None:
        when = datetime.combine(picked_day, picked_time or time(12, 0), IST)
        return min(when, now)
    return now


header("report")
st.caption(f"🔒 {tr('report_privacy')}")

channel = st.pills(
    tr("report_channel"),
    channel_ids(),
    format_func=lambda c: label(CHANNEL_ICONS.get(c, "❓"), channel_label(c, lang())),
    key="report_channel",
)
when = st.pills(
    tr("report_when"),
    ["now", "today", "yesterday", "pick"],
    format_func=lambda w: label(WHEN_ICONS[w], tr(f"when_{w}")),
    key="report_when",
    default="now",
)
picked_day: date | None = None
picked_time: time | None = None
if when == "pick":
    picked_day = st.date_input(
        tr("when_pick"), max_value=date.today(), key="report_day", value=date.today()
    )
    picked_time = st.time_input("⏰", key="report_time", value=time(12, 0))

if "prefill" in st.session_state:
    st.session_state["report_value"] = st.session_state.pop("prefill")
value = st.text_input(label("📋", tr("report_what")), key="report_value")
scam_type = st.pills(
    tr("report_type"),
    scam_type_ids(),
    format_func=lambda s: label(SCAM_ICONS.get(s, "❓"), scam_label(s, lang())),
    key="report_scam_type",
)
with guarded():
    choices = areas()
names = [area_name(a) for a in choices]
remembered = st.session_state.get("my_area")
area = st.selectbox(
    label("📍", tr("report_area")),
    names,
    index=names.index(remembered) if remembered in names else None,
    key="report_area",
)
note = st.text_area(label("✍️", tr("report_note")), key="report_note", max_chars=1000)

if st.button(label("📣", tr("report_submit")), type="primary", use_container_width=True):
    detected = detect(value)
    if not (channel and scam_type and area):
        st.warning(tr("report_missing"))
    elif detected is None:
        st.warning(tr("report_bad_value"))
    else:
        st.session_state["my_area"] = area
        chosen = choices[names.index(area)]
        occurred = occurred_at(when or "now", picked_day, picked_time)
        body = {
            "report_id": f"web_{uuid.uuid4().hex}",
            "occurred_at": occurred.replace(microsecond=0).isoformat(),
            "reported_at": datetime.now(IST).replace(microsecond=0).isoformat(),
            "reporter_id": device_id(),
            "channel": channel,
            "scam_type": scam_type,
            "identifier_type": detected[0],
            "identifier_value": value.strip(),
            "pincode": chosen["pincode"],
            "locality": chosen["locality"],
            "city": chosen["city"],
            "note": note.strip(),
            "has_screenshot": False,
            "amount_lost_inr": 0,
        }
        try:
            with guarded():
                api().report(body)
        except ApiError as e:
            st.error(tr("report_slow_down") if e.status == 429 else tr("report_rejected"))
        else:
            st.success(f"✅ {tr('report_ok')}")
            st.balloons()
