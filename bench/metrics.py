from __future__ import annotations

import json
import statistics
from pathlib import Path

from .run import RESULTS, load_results
from .arms import arm_slug


def apply_policy(pred, policy: str):
    """What the *application* does when the arm gave no usable answer.
    open   -> treat as clean (fail open, the comment goes through)
    closed -> treat as toxic (fail closed, the comment is held)
    drop   -> exclude from metrics (what most benchmarks quietly do)
    """
    if pred is not None:
        return pred
    return {"open": 0, "closed": 1, "drop": None}[policy]


def prf(rows: list[dict], policy: str = "open") -> dict:
    tp = fp = fn = tn = 0
    n_mal = n_err = n_dropped = 0
    for r in rows:
        n_mal += bool(r.get("malformed"))
        n_err += r.get("error") is not None
        p = apply_policy(r["pred"], policy)
        if p is None:
            n_dropped += 1
            continue
        y = r["label"]
        if p == 1 and y == 1: tp += 1
        elif p == 1 and y == 0: fp += 1
        elif p == 0 and y == 1: fn += 1
        else: tn += 1
    n = tp + fp + fn + tn
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {
        "n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "accuracy": (tp + tn) / n if n else 0.0,
        "precision": prec, "recall": rec, "f1": f1,
        "malformed": n_mal, "errors": n_err, "dropped": n_dropped,
        "malformed_rate": n_mal / len(rows) if rows else 0.0,
        "policy": policy,
    }


def percentiles(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    v = sorted(values)
    def q(p):
        k = max(0, min(len(v) - 1, round(p * (len(v) - 1))))
        return v[k]
    return {"n": len(v), "p50": q(0.50), "p95": q(0.95), "p99": q(0.99),
            "mean": statistics.fmean(v), "max": v[-1]}


def load_run(sample: str, arm: str, run: int = 0) -> list[dict]:
    path = RESULTS / sample / arm_slug(arm) / f"run{run}.jsonl"
    rows = load_results(path)
    return list(rows.values())


def token_means(rows: list[dict]) -> tuple[float, float]:
    ok = [r for r in rows if r.get("error") is None]
    if not ok:
        return 0.0, 0.0
    return (statistics.fmean(r["tokens_in"] for r in ok),
            statistics.fmean(r["tokens_out"] for r in ok))


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False))
