"""Map screen: area points sized by count and coloured by severity; days and radius; alerts.

Points are the areas' Appendix B points from the API, never anyone's own location.

Owner: A. Filled in by: A4.
"""

from __future__ import annotations

import streamlit as st

from scam_web.i18n import scam_label
from scam_web.panel import page
from scam_web.ui import api, area_name, areas, guarded, label, lang, md, tr

SEVERITY = {"CRIT": ("#d1242f", "🔴"), "HIGH": ("#e8710a", "🟠"), "MED": ("#bf8700", "🟡")}

main = page("map")
with main:
    with guarded():
        choices = areas()
    names = [area_name(a) for a in choices]
    remembered = st.session_state.get("my_area")
    area = st.selectbox(
        label("📍", tr("map_area")),
        names,
        index=names.index(remembered) if remembered in names else 0,
        key="map_area",
    )
    days = st.slider(label("📅", tr("map_days")), 1, 30, 7, key="map_days")
    radius = st.slider(label("📏", tr("map_radius")), 1, 50, 2, key="map_radius")
    pincode = str(choices[names.index(area)]["pincode"])

    with guarded():
        clusters = api().area_map(pincode, days, radius)
        found_alerts = api().alerts(pincode)

    if clusters:
        st.map(
            {
                "lat": [c["lat"] for c in clusters],
                "lon": [c["lng"] for c in clusters],
                "size": [80 + 40 * min(int(c["count"]), 25) for c in clusters],
                "color": [SEVERITY[c["severity"]][0] for c in clusters],
            },
            latitude="lat",
            longitude="lon",
            size="size",
            color="color",
            zoom=12,
        )
        for c in clusters:
            icon = SEVERITY[c["severity"]][1]
            st.markdown(
                f"{icon} **{md(c['locality'])}** · {tr('map_count', n=c['count'])}"
                f" · {md(scam_label(c['top_scam_type'], lang()))}"
            )
    else:
        st.info(tr("map_none"))

    st.markdown(f"#### 🔔 {tr('alerts_title')}")
    if not found_alerts:
        st.caption(tr("no_alerts"))
    for alert in found_alerts:
        if alert["type"] == "SPIKE":
            st.warning(
                f"📈 {tr('alert_spike', count=alert['count'], base=alert['baseline_per_day'])}"
            )
        else:
            st.warning(f"🆕 {tr('alert_new', kind=scam_label(alert['scam_type'], lang()))}")
