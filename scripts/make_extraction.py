"""Experiment (slide 16): structured extraction from restaurant booking requests.

Five fields. Two of them ("time", "party_size") have a grammar a regex can match exactly.
Three of them ("date", "cuisine", "location") are said sideways, where meaning beats pattern.
Every utterance deliberately omits some fields: a field that is not in the sentence has gold
null, which is how the *invention* rate is measured -- an extractor that fills it in has
hallucinated a booking detail, the failure mode that actually hurts in production.

    python scripts/make_extraction.py     # -> data/handlabeled/extraction.csv
"""
import hashlib
import json
import random

import pandas as pd

SEED = 20261012
FIELDS = ["time", "party_size", "date", "cuisine", "location"]

TIMES = [("8pm", "20:00"), ("at 8 pm", "20:00"), ("19:30", "19:30"), ("half seven", "19:30"),
         ("7.45pm", "19:45"), ("noon", "12:00"), ("at nine", "21:00"), ("21:15", "21:15")]
SIZES = [("for four", 4), ("for 4", 4), ("table for two", 2), ("party of six", 6),
         ("just me", 1), ("the two of us", 2), ("we're eight", 8), ("a dozen of us", 12)]
DATES = [("tomorrow", "tomorrow"), ("next friday", "next friday"), ("tonight", "tonight"),
         ("this saturday", "this saturday"), ("on the 14th", "the 14th"), ("next week", "next week"),
         ("the day after tomorrow", "the day after tomorrow"), ("a week on tuesday", "a week on tuesday"),
         ("end of the month", "end of the month")]
# Deliberately wider than the regex arm's gazetteer: a real request says it sideways.
CUISINES = [("somewhere Italian", "italian"), ("fancy some sushi", "japanese"),
            ("craving pasta", "italian"), ("in the mood for dim sum", "chinese"),
            ("something with good mezedes", "greek"), ("a proper curry", "indian"),
            ("tapas maybe", "spanish"), ("burgers", "american"),
            ("anywhere that does a decent ramen", "japanese"),
            ("something with a wood-fired oven", "italian"),
            ("I could murder a souvlaki", "greek"),
            ("that place that does the little dumplings", "chinese"),
            ("somewhere I can get a steak", "american"),
            ("preferably something spicy from Kerala", "indian"),
            ("raw fish, if that's an option", "japanese"),
            ("small plates, lots of them", "spanish")]
LOCATIONS = [("in Kolonaki", "kolonaki"), ("near Syntagma", "syntagma"), ("around Psyri", "psyri"),
             ("in Thiseio", "thiseio"), ("close to the office", "the office"), ("in Exarchia", "exarchia"),
             ("walking distance from the hotel", "the hotel"), ("somewhere by the sea", "the sea"),
             ("near where we met last time", "where we met last time")]
FILLER = ["Hi!", "Hey there.", "Quick one -", "Booking request:", "", "Hello,",
          "Can you sort this out?", "Thanks in advance."]


def build(n: int = 200) -> pd.DataFrame:
    rng = random.Random(SEED)
    rows = []
    while len(rows) < n:
        # which fields are actually present in this utterance (at least one, never all five)
        present = [f for f in FIELDS if rng.random() < 0.62]
        if not present or len(present) == 5:
            continue
        parts, gold = [], {f: None for f in FIELDS}
        pick = {"time": TIMES, "party_size": SIZES, "date": DATES,
                "cuisine": CUISINES, "location": LOCATIONS}
        for f in present:
            surface, value = rng.choice(pick[f])
            gold[f] = value
            parts.append(surface)
        rng.shuffle(parts)
        text = " ".join([rng.choice(FILLER)] + parts).strip()
        text = text[0].upper() + text[1:]
        rows.append({"id": hashlib.sha1(text.encode()).hexdigest()[:12], "text": text,
                     "gold": json.dumps(gold), "n_present": len(present)})
    df = pd.DataFrame(rows).drop_duplicates(subset="id").reset_index(drop=True)
    return df


if __name__ == "__main__":
    df = build()
    df.to_csv("data/handlabeled/extraction.csv", index=False)
    absent = sum(1 for g in df.gold for k, v in json.loads(g).items() if v is None)
    print(f"{len(df)} utterances -> data/handlabeled/extraction.csv")
    print(f"  {len(df) * 5 - absent} field values present, {absent} absent (the invention denominator)")
