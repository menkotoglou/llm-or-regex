"""Experiment 4: run-to-run disagreement at temperature 0.

    python -m bench.determinism --sample balanced-2k --arm llm:anthropic:<model> --n 200 --runs 3

Runs the arm K times over the same N items (through bench.run, so it is
resumable and cached), then reports:
  - items where at least two runs disagree
  - items where any run was malformed
  - flip direction, for the failure-mode slide

Also works for regex/apc/own as a sanity check (should be 0.0%).
Output: results/determinism/<arm>.json
"""
from __future__ import annotations

import argparse
from collections import Counter

from .arms import arm_slug
from .metrics import load_run, write_json
from .run import RESULTS, run_arm


def analyse(sample: str, arm: str, runs: int, n: int) -> dict:
    per_run = [ {r["item_id"]: r for r in load_run(sample, arm, k)} for k in range(runs) ]
    ids = [i for i in per_run[0] if all(i in pr for pr in per_run)][:n]
    disagree, any_malformed, flips = [], [], Counter()
    for i in ids:
        preds = [pr[i]["pred"] for pr in per_run]
        if any(pr[i].get("malformed") for pr in per_run):
            any_malformed.append(i)
        usable = [p for p in preds if p is not None]
        if len(set(usable)) > 1:
            disagree.append(i)
            flips[f"{'toxic' if preds[0] == 1 else 'clean'}->mixed"] += 1
    examples = []
    for i in disagree[:10]:
        examples.append({"item_id": i, "label": per_run[0][i]["label"],
                         "preds": [pr[i]["pred"] for pr in per_run],
                         "raws": [pr[i]["raw"][:80] for pr in per_run]})
    return {
        "arm": arm, "sample": sample, "runs": runs, "n": len(ids),
        "disagreeing_items": len(disagree), "disagreement_rate": len(disagree) / len(ids) if ids else 0,
        "items_with_malformed": len(any_malformed),
        "malformed_item_rate": len(any_malformed) / len(ids) if ids else 0,
        "flip_direction": dict(flips), "examples": examples,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", default="balanced-2k")
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    for spec in a.arm:
        for k in range(a.runs):
            run_arm(a.sample, spec, k, a.n, a.workers, quiet=True)
        res = analyse(a.sample, spec, a.runs, a.n)
        write_json(RESULTS / "determinism" / f"{arm_slug(spec)}.json", res)
        print(f"{spec:45s} disagreement={res['disagreement_rate']:.1%} "
              f"({res['disagreeing_items']}/{res['n']})  malformed items={res['malformed_item_rate']:.1%}")


if __name__ == "__main__":
    main()
