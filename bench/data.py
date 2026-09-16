"""Samples.

Why Civil Comments and not Jigsaw Toxic Comment (Wikipedia)?
alt-profanity-check is trained on the Jigsaw Toxic Comment train set (see its README,
"More on How/Why It Works"). Evaluating on that data would be leakage in apc's favour.
Civil Comments (Jigsaw "Unintended Bias", 2019) is a different platform and is not in
apc's training data. The LLMs have almost certainly seen both in pretraining; say so
on the slide.

Gold label: toxicity >= 0.5, the threshold the dataset authors use.

Three fixed samples, one seed, written to data/samples/ and committed:
  balanced-2k   1,000 toxic / 1,000 clean     accuracy comparison
  natural-2k    2,000 at natural prevalence   cost and precision story
  train-4k      2,000 toxic / 2,000 clean     training data for the own:* arm, disjoint from both

Sources:
  --source hf          datasets.load_dataset("google/civil_comments", split="train")
  --source csv PATH    Kaggle jigsaw-unintended-bias train.csv (comment_text, target)

Hand-labelled sets live in data/handlabeled/<name>.csv with columns id,text,label[,notes]
and are addressed by the same --sample <name> flag.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"
HANDLABELED = ROOT / "data" / "handlabeled"
SEED = 20261012  # the talk date
THRESHOLD = 0.5


def _id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def _load_source(source: str, csv: str | None) -> pd.DataFrame:
    if source == "hf":
        from datasets import load_dataset
        ds = load_dataset("google/civil_comments", split="train")
        df = ds.to_pandas()[["text", "toxicity"]]
    elif source == "csv":
        if not csv:
            raise SystemExit("--source csv needs --csv PATH")
        df = pd.read_csv(csv, usecols=["comment_text", "target"])
        df = df.rename(columns={"comment_text": "text", "target": "toxicity"})
    else:
        raise SystemExit(f"unknown source {source}")
    df = df.dropna(subset=["text"])
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len().between(10, 2000)]   # drop empties and walls of text
    df = df.drop_duplicates(subset=["text"])
    df["label"] = (df["toxicity"] >= THRESHOLD).astype(int)
    df["id"] = df["text"].map(_id)
    return df[["id", "text", "label", "toxicity"]]


def build(source: str, csv: str | None, n: int = 2000) -> None:
    df = _load_source(source, csv)
    half = n // 2
    toxic = df[df.label == 1].sample(half, random_state=SEED)
    clean = df[df.label == 0].sample(half, random_state=SEED)
    balanced = pd.concat([toxic, clean]).sample(frac=1, random_state=SEED)
    natural = df.sample(n, random_state=SEED + 1)
    used = set(balanced.id) | set(natural.id)
    rest = df[~df.id.isin(used)]
    train = pd.concat([rest[rest.label == 1].sample(n, random_state=SEED + 2),
                       rest[rest.label == 0].sample(n, random_state=SEED + 2)]).sample(frac=1, random_state=SEED)

    SAMPLES.mkdir(parents=True, exist_ok=True)
    balanced.to_csv(SAMPLES / "balanced-2k.csv", index=False)
    natural.to_csv(SAMPLES / "natural-2k.csv", index=False)
    train.to_csv(SAMPLES / "train-4k.csv", index=False)
    manifest = {
        "source": source, "seed": SEED, "threshold": THRESHOLD, "n": n,
        "pool_size": int(len(df)), "pool_prevalence": round(float(df.label.mean()), 4),
        "balanced-2k": {"toxic": int(balanced.label.sum()), "clean": int((1 - balanced.label).sum())},
        "natural-2k": {"toxic": int(natural.label.sum()), "clean": int((1 - natural.label).sum()),
                       "prevalence": round(float(natural.label.mean()), 4)},
        "train-4k": {"n": int(len(train)), "disjoint_from_eval": True},
    }
    (SAMPLES / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


def load_sample(name: str) -> pd.DataFrame:
    for folder in (SAMPLES, HANDLABELED):
        p = folder / f"{name}.csv"
        if p.exists():
            df = pd.read_csv(p)
            missing = {"id", "text", "label"} - set(df.columns)
            if missing:
                raise SystemExit(f"{p} lacks columns {missing}")
            df["id"] = df["id"].astype(str)
            df["label"] = df["label"].astype(int)
            return df
    raise SystemExit(f"no sample named {name!r} in {SAMPLES} or {HANDLABELED}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["hf", "csv"], default="hf")
    ap.add_argument("--csv")
    ap.add_argument("--n", type=int, default=2000)
    a = ap.parse_args()
    build(a.source, a.csv, a.n)
