"""Every trust threshold and weight in one place, tuned on tuning seeds only.

Starting values are ARCHITECTURE.md "Trust rules". Change them only after a run on the judge
simulator's tuning seeds (judge/seeds.toml), and report results on held-out seeds only.

Owner: B. Filled in by: B5.
"""

from __future__ import annotations

from datetime import timedelta

# PRD privacy rule 2: hide the value until at least 3 different people reported it.
UNMASK_MIN_REPORTERS = 3

# Rule 6: KNOWN_SCAM needs 3 independent clusters and a weighted score of 3.0.
KNOWN_SCAM_MIN_CLUSTERS = 3
KNOWN_SCAM_MIN_SCORE = 3.0

# Rule 1: more than this many reports from one reporter within an hour gets 429.
RATE_LIMIT_PER_HOUR = 3
RATE_LIMIT_WINDOW = timedelta(hours=1)

# Rule 2: reports from one ip_prefix this close together are one person.
SAME_CONNECTION_WINDOW = timedelta(hours=24)

# Rule 3: notes at least this similar are one voice. Fingerprints are bottom-k MinHash
# sketches of 5-character shingles; notes shorter than OWN_WORDS_MIN_CHARS have none.
NOTE_DUPLICATE_SIMILARITY = 0.8
NOTE_SHINGLE_CHARS = 5
NOTE_SKETCH_SIZE = 128

# Rule 4: first-time reporters on one identifier within BURST_WINDOW of each other are a
# coordinated burst when at least BURST_MIN_REPORTS of them either mostly have empty or copied
# notes, or all describe incidents within BURST_INCIDENT_SPAN. A burst weighs at most
# BURST_MAX_WEIGHT in total and counts as one independent cluster.
BURST_WINDOW = timedelta(hours=1)
BURST_MIN_REPORTS = 5
BURST_MOSTLY = 0.6
BURST_INCIDENT_SPAN = timedelta(minutes=15)
BURST_MAX_WEIGHT = 1.5

# Rule 5: a cluster in its own words weighs more than one with an empty or very short note.
OWN_WORDS_MIN_CHARS = 15
WEIGHT_OWN_WORDS = 1.0
WEIGHT_SHORT_NOTE = 0.6

# Lookup evidence: the most recent reports shown, newest first.
EVIDENCE_LIMIT = 5
