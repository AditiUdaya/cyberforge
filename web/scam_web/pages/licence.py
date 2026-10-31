"""Licence screen: who the app is licensed to and until when; upload a licence file (demo).

GET and POST /license work even when the licence has expired, so this screen always works.

Owner: A. Filled in by: A4.
"""

from __future__ import annotations

import json

import streamlit as st

from scam_web.api_client import ApiError
from scam_web.ui import api, guarded, header, label, md, short_date, tr

header("licence")
with guarded():
    current = api().licence()

with st.container(border=True):
    if current.get("licensee") is None:
        st.markdown(f"### 🔒 {tr('licence_none')}")
    else:
        valid = bool(current.get("valid"))
        st.markdown(
            f"### {'✅' if valid else '🔒'} {tr('licence_valid' if valid else 'licence_invalid')}"
        )
        st.markdown(f"**{tr('licence_to')}:** {md(current['licensee'])}")
        st.markdown(f"**{tr('licence_until')}:** {short_date(current.get('expires_at'))}")
        if not valid:
            st.error(tr("expired"))

upload = st.file_uploader(label("📄", tr("licence_upload")), type=["json"], key="licence_file")
if upload is not None and st.button(label("🔑", tr("licence_upload")), type="primary"):
    try:
        doc = json.loads(upload.getvalue().decode("utf-8"))
        if not isinstance(doc, dict):
            raise ValueError
    except ValueError:
        st.error(tr("licence_unreadable"))
    else:
        try:
            with guarded():
                api().upload_licence(doc)
        except ApiError as e:
            st.error(tr("licence_bad", why=e.message))
        else:
            st.success(f"✅ {tr('licence_ok')}")
            st.rerun()
