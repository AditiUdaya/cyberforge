"""Community Scam Map mobile website: navigation between the six screens.

Run: cd web && uv run streamlit run app.py   (talks to SCAM_MAP_API_URL)

Owner: A. Filled in by: A0.
"""

from __future__ import annotations

import streamlit as st

from scam_web.i18n import PAGE_ICONS
from scam_web.ui import PAGES, tr

st.set_page_config(page_title=tr("app_title"), page_icon="🛡️", layout="centered")

navigation = st.navigation(
    [
        st.Page(
            PAGES[name], title=tr(f"nav_{name}"), icon=PAGE_ICONS[name], default=name == "check"
        )
        for name in ("check", "report", "map", "challenge", "licence", "how")
    ],
    position="top",
)
navigation.run()
