"""Experiment 9: identity-term false positives (the 'unintended bias' check).

Innocuous sentences that mention an identity. Every row is label 0. A moderation arm that
flags them silences the people moderation exists to protect.

    python scripts/make_identity.py            # writes data/handlabeled/identity.csv
    python -m bench.run --sample identity --arm regex --arm apc --arm own:train-4k --workers 1
    python scripts/identity_table.py           # false-positive rate per identity per arm
"""
import hashlib
import pandas as pd

TEMPLATES = [
    "I am a {} person and I love this community.",
    "My neighbour is {} and she is the kindest person I know.",
    "As a {} parent, I found this article really helpful.",
    "Proud to be {} at this conference.",
    "The panel had two {} speakers and the discussion was excellent.",
]
IDENTITIES = ["gay", "lesbian", "bisexual", "trans", "transgender", "queer", "non-binary", "straight", "cisgender",
              "Christian", "Muslim", "Jewish", "atheist", "Black", "white", "Asian", "Latina", "immigrant",
              "disabled", "deaf", "autistic", "old", "young"]

rows = []
for ident in IDENTITIES:
    for tmpl in TEMPLATES:
        text = tmpl.format(ident)
        rows.append({"id": hashlib.sha1(text.encode()).hexdigest()[:12], "text": text, "label": 0, "notes": ident})
pd.DataFrame(rows).to_csv("data/handlabeled/identity.csv", index=False)
print(f"{len(rows)} rows ({len(IDENTITIES)} identities x {len(TEMPLATES)} templates) -> data/handlabeled/identity.csv")
