"""Check screen (home): paste a value or a whole message; one verdict card per identifier.

Owner: A. Filled in by: A1.
"""

from __future__ import annotations

import streamlit as st

from scam_web.extract import extract
from scam_web.panel import page
from scam_web.ui import api, areas, guarded, label, tr, verdict_card

main = page("check")
with main:
    text = st.text_area(tr("check_prompt"), key="check_text", height=110)
    if st.button(label("🔍", tr("check_button")), type="primary", use_container_width=True):
        st.session_state["check_found"] = extract(text)
        st.session_state["checked"] = True

    if st.session_state.get("checked"):
        found = st.session_state.get("check_found", [])
        if not found:
            st.warning(tr("check_none_found"))
        with guarded():
            areas()
            for kind, value in found:
                verdict_card(kind, value, api().lookup(kind, value))
