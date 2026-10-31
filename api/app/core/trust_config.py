"""Every trust threshold and weight in one place, tuned on tuning seeds only.

B2 sets the verdict and masking thresholds from the PRD; B5 adds clustering, burst and weight
settings and tunes them on the judge simulator's tuning seeds.

Owner: B. Filled in by: B5.
"""

from __future__ import annotations

# PRD privacy rule 2: hide the value until at least 3 different people reported it.
UNMASK_MIN_REPORTERS = 3

# ARCHITECTURE trust rule 6: KNOWN_SCAM needs 3 independent clusters and a weighted score of 3.0.
KNOWN_SCAM_MIN_CLUSTERS = 3
KNOWN_SCAM_MIN_SCORE = 3.0

# Lookup evidence: the most recent reports shown, newest first.
EVIDENCE_LIMIT = 5
