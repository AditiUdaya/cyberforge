"""POST /reports: validate, normalise, HMAC reporter fields, rate limit (429), store.
Replies 201 {report_id, case_id, merged} or 400. Stub in B1; trust rules in B5.

Owner: B. Filled in by: B2.
"""

from __future__ import annotations
