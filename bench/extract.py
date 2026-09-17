"""Experiment (slide 16): extraction accuracy per field, and the invention rate.

    python -m bench.extract --arm regex --arm llm:anthropic:claude-opus-5

Two numbers per arm, per field:
  accuracy  -- of the values the user actually stated, how many were extracted exactly right
  invention -- of the fields the user did NOT state, how many the extractor filled in anyway
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

from .arms import build_arm
from .run import RESULTS

FIELDS = ["time", "party_size", "date", "cuisine", "location"]
DATA = Path(__file__).resolve().parent.parent / "data" / "handlabeled" / "extraction.csv"
PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "extraction.txt"

WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
            "seven": 7, "eight": 8, "nine": 9, "ten": 10, "dozen": 12}
# The regex arm: a real pattern for the two fields that have a grammar, a gazetteer for the
# one that is a closed set, and nothing at all for the two that require understanding.
CUISINE_WORDS = {"italian": "italian", "pasta": "italian", "sushi": "japanese",
                 "dim sum": "chinese", "mezedes": "greek", "curry": "indian",
                 "tapas": "spanish", "burgers": "american"}
DATE_WORDS = ["tomorrow", "tonight", "next friday", "this saturday", "next week", "the 14th"]


def regex_extract(text: str) -> dict:
    t = text.lower()
    out = {f: None for f in FIELDS}

    m = re.search(r"\b(\d{1,2})[:.](\d{2})\s*(am|pm)?\b", t)
    if m:
        h, mi = int(m.group(1)), m.group(2)
        if m.group(3) == "pm" and h < 12:
            h += 12
        out["time"] = f"{h:02d}:{mi}"
    else:
        m = re.search(r"\b(?:at\s+)?(\d{1,2})\s*(am|pm)\b", t)
        if m:
            h = int(m.group(1))
            if m.group(2) == "pm" and h < 12:
                h += 12
            out["time"] = f"{h:02d}:00"
        elif "noon" in t:
            out["time"] = "12:00"
        else:
            m = re.search(r"\bhalf\s+(\w+)\b", t)   # "half seven" -> 19:30
            if m and m.group(1) in WORD_NUM:
                h = WORD_NUM[m.group(1)]
                out["time"] = f"{h + 12 if h < 12 else h:02d}:30"
            else:
                m = re.search(r"\bat\s+(\w+)\b", t)   # "at nine"
                if m and m.group(1) in WORD_NUM:
                    h = WORD_NUM[m.group(1)]
                    out["time"] = f"{h + 12 if h < 12 else h:02d}:00"

    num = r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
    for pat in (rf"\b(?:for|party of)\s+{num}\b", rf"\bthe\s+{num}\s+of us\b",
                rf"\bwe(?:'re| are)\s+{num}\b", rf"\b{num}\s+of us\b"):
        m = re.search(pat, t)
        if m:
            g = m.group(1)
            out["party_size"] = int(g) if g.isdigit() else WORD_NUM[g]
            break
    else:
        if re.search(r"\ba dozen\b", t):
            out["party_size"] = 12
        elif re.search(r"\bjust me\b|\bmyself\b", t):
            out["party_size"] = 1

    for d in DATE_WORDS:
        if d in t:
            out["date"] = d
            break
    for k, v in CUISINE_WORDS.items():
        if k in t:
            out["cuisine"] = v
            break
    return out


def parse_json(raw: str) -> dict | None:
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def norm(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, str):
        return re.sub(r"^(the|a|an)\s+", "", v.strip().lower())
    return v


def time_equiv(g, p) -> bool:
    """AM/PM is genuinely unstated in "half seven" / "at nine"; accept either reading."""
    if g == p:
        return True
    try:
        gh, gm = (int(x) for x in str(g).split(":"))
        ph, pm = (int(x) for x in str(p).split(":"))
    except (ValueError, AttributeError):
        return False
    return gm == pm and abs(gh - ph) == 12


def score(gold: dict, pred: dict | None) -> dict:
    """Per field: 'hit'/'miss' when gold has a value, 'invented'/'ok' when gold is null."""
    out = {}
    for f in FIELDS:
        g, p = norm(gold.get(f)), norm((pred or {}).get(f))
        if isinstance(g, str) and isinstance(p, (int, float)):
            p = str(p)
        if isinstance(g, (int, float)) and isinstance(p, str) and p.isdigit():
            p = int(p)
        if g is not None:
            ok = time_equiv(g, p) if f == "time" else (p == g)
            out[f] = "hit" if ok else "miss"
        else:
            out[f] = "ok" if p is None else "invented"
    return out


def run(arm_spec: str, df: pd.DataFrame, workers: int) -> dict:
    rows = []
    if arm_spec == "regex":
        for r in df.itertuples(index=False):
            rows.append((r.id, json.loads(r.gold), regex_extract(r.text), None))
    else:
        arm = build_arm(arm_spec)
        sysmsg, tmpl = PROMPT.read_text(encoding="utf-8").split("---USER---", 1)
        sysmsg = sysmsg.replace("---SYSTEM---", "").strip()
        tmpl = tmpl.strip()
        from concurrent.futures import ThreadPoolExecutor

        def one(r):
            try:
                raw, _, _ = arm.complete_retrying(sysmsg, tmpl.replace("{text}", r.text))
            except Exception as e:  # noqa: BLE001
                return (r.id, json.loads(r.gold), None, str(e)[:200])
            return (r.id, json.loads(r.gold), parse_json(raw), None)

        # Settle the capability flags on one serial call before fanning out, so N workers
        # do not each rediscover the same 400.
        items = list(df.itertuples(index=False))
        rows = [one(items[0])]
        with ThreadPoolExecutor(max_workers=workers) as ex:
            rows += list(ex.map(one, items[1:]))

    per_field = {f: {"hit": 0, "miss": 0, "invented": 0, "ok": 0} for f in FIELDS}
    errors = malformed = 0
    for _id, gold, pred, err in rows:
        if err:
            errors += 1
            continue
        if pred is None:
            malformed += 1
        for f, verdict in score(gold, pred).items():
            per_field[f][verdict] += 1

    res = {"arm": arm_spec, "n": len(rows), "errors": errors, "malformed": malformed, "fields": {}}
    for f, c in per_field.items():
        present, absent = c["hit"] + c["miss"], c["invented"] + c["ok"]
        res["fields"][f] = {
            "accuracy": c["hit"] / present if present else None,
            "invention": c["invented"] / absent if absent else None,
            "n_present": present, "n_absent": absent,
        }
    inv = sum(c["invented"] for c in per_field.values())
    tot_abs = sum(c["invented"] + c["ok"] for c in per_field.values())
    res["invention_overall"] = inv / tot_abs if tot_abs else None
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    if not DATA.exists():
        raise SystemExit(f"{DATA} missing -- run scripts/make_extraction.py first")
    df = pd.read_csv(DATA)

    out_dir = RESULTS / "extraction"
    out_dir.mkdir(parents=True, exist_ok=True)
    allres = []
    for spec in a.arm:
        r = run(spec, df, a.workers)
        allres.append(r)
        (out_dir / f"{spec.replace(':', '_').replace('/', '_')}.json").write_text(
            json.dumps(r, indent=2), encoding="utf-8")
        print(f"{spec:44s} invented {r['invention_overall']:.1%} of absent fields "
              f"(errors={r['errors']}, malformed={r['malformed']})", file=sys.stderr)

    hdr = "| field | " + " | ".join(r["arm"].split(":")[-1] for r in allres) + " |"
    md = ["# Extraction: accuracy on stated fields (invention rate on absent fields)", "",
          hdr, "|---|" + "---|" * len(allres)]
    for f in FIELDS:
        cells = []
        for r in allres:
            d = r["fields"][f]
            acc = "-" if d["accuracy"] is None else f"{d['accuracy']:.0%}"
            inv = "-" if d["invention"] is None else f"{d['invention']:.0%}"
            cells.append(f"{acc} ({inv})")
        md.append(f"| {f} | " + " | ".join(cells) + " |")
    md.append("| **invented a value that wasn't there** | " +
              " | ".join(f"**{r['invention_overall']:.0%}**" for r in allres) + " |")
    (RESULTS / "extraction.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
