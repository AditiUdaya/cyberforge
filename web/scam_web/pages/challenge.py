"""Challenge screen: a business says "this is our real number" (PRD bonus feature).

Owner: A. Filled in by: A4.
"""

from __future__ import annotations

import streamlit as st

from scam_web.api_client import ApiError
from scam_web.extract import detect
from scam_web.panel import page
from scam_web.ui import api, guarded, label, tr

main = page("challenge")
with main:
    st.write(tr("challenge_intro"))
    with st.form("challenge"):
        value = st.text_input(label("📋", tr("challenge_value")))
        name = st.text_input(label("🏪", tr("challenge_name")))
        email = st.text_input(label("✉️", tr("challenge_email")))
        proof = st.text_area(label("📄", tr("challenge_proof")))
        sent = st.form_submit_button(label("📨", tr("challenge_submit")), type="primary")

    if sent:
        detected = detect(value)
        if not (name.strip() and email.strip() and proof.strip()):
            st.warning(tr("challenge_missing"))
        elif detected is None:
            st.warning(tr("report_bad_value"))
        else:
            body = {
                "identifier_type": detected[0],
                "identifier_value": value.strip(),
                "claimant_name": name.strip(),
                "contact_email": email.strip(),
                "proof_note": proof.strip(),
            }
            try:
                with guarded():
                    api().challenge(body)
            except ApiError as e:
                st.warning(tr("challenge_limit") if e.status == 429 else tr("report_rejected"))
            else:
                st.success(f"✅ {tr('challenge_ok')}")
