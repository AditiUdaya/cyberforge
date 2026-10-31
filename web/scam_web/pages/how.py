"""How it works: the trust rules and privacy rules in plain words.

Owner: A. Filled in by: A4.
"""

from __future__ import annotations

import streamlit as st

from scam_web.panel import page
from scam_web.ui import tr

main = page("how")
with main:
    st.markdown(tr("how_body"))
