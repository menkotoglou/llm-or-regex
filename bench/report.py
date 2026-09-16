"""The summary table. This becomes the most important slide in the talk.

    python -m bench.report --arm regex --arm apc --arm own:train-4k --arm llm:anthropic:<model>

Pulls whatever exists in results/ and leaves a dash where an experiment has not
been run. Also writes results/errors/<arm>_<sample>.md with the worst false positives
and false negatives per arm, for the failure-mode slide (pick five by hand).

Output: results/summary.md, results/summary.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time

from .arms import arm_slug
from .metrics import load_run, prf, write_json
from .run import RESULTS, ROOT


def _read(path):
    return json.loads(path.read_text()) if path.exists() else None


def _git_rev() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "uncommitted"


def collect(arms: list[str], samples: tuple[str, ...], policy: str) -> dict:
    out = {"generated": time.strftime("%Y-%m-%d %H:%M"), "git": _git_rev(), "policy": policy, "arms": {}}
    for arm in arms:
        slug = arm_slug(arm)
        entry = {"metrics": {}}
        for s in samples:
            rows = load_run(s, arm)
            if rows:
                entry["metrics"][s] = prf(rows, policy)
        entry["latency"] = _read(RESULTS / "latency" / f"{slug}.json")
        entry["cost"] = _read(RESULTS / "cost" / f"{slug}.json")
        entry["determinism"] = _read(RESULTS / "determinism" / f"{slug}.json")
        out["arms"][arm] = entry
    return out


def fmt(v, f="{:.3f}"):
    return "-" if v is None else f.format(v)


def to_markdown(summary: dict, samples: tuple[str, ...]) -> str:
    head = ["arm"]
    for s in samples:
        head += [f"P ({s})", f"R ({s})", f"F1 ({s})"]
    head += ["p50 ms", "p95 ms", "p99 ms", "EUR/1M", "malformed", "disagree@t0"]
    lines = [f"# Summary  (generated {summary['generated']}, commit {summary['git']}, "
             f"malformed policy = {summary['policy']})", "",
             "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for arm, e in summary["arms"].items():
        row = [arm]
        for s in samples:
            m = e["metrics"].get(s)
            row += [fmt(m and m["precision"]), fmt(m and m["recall"]), fmt(m and m["f1"])]
        lat = (e["latency"] or {}).get("latency_ms", {})
        row += [fmt(lat.get("p50"), "{:.1f}"), fmt(lat.get("p95"), "{:.1f}"), fmt(lat.get("p99"), "{:.1f}")]
        row += [fmt((e["cost"] or {}).get("eur_per_1m"), "{:.2f}")]
        mal = None
        for s in samples:
            m = e["metrics"].get(s)
            if m:
                mal = m["malformed_rate"]
                break
        row += [fmt(mal, "{:.1%}")]
        row += [fmt((e["determinism"] or {}).get("disagreement_rate"), "{:.1%}")]
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "Latency: concurrency 1, 50 warmup calls, same 200 items per arm. "
              "LLM latency includes the network from the measuring machine. "
              "Costs from real token counts x the dated price table in config/prices.toml."]
    for arm, e in summary["arms"].items():
        lat = e["latency"] or {}
        if "cold_start" in lat:
            c = lat["cold_start"]
            lines.append(f"\n{arm}: cold start import {c['import_ms']['p50']:.0f} ms, first predict "
                         f"{c['first_predict_ms']['p50']:.0f} ms, max RSS {c['max_rss_mb']['p50']:.0f} MB, "
                         f"batch {lat['batch']['items_per_s']:.0f} items/s; measured on {lat['machine']['platform']}.")
    return "\n".join(lines) + "\n"


def error_examples(arm: str, sample: str, k: int = 15) -> str:
    from .data import load_sample
    rows = load_run(sample, arm)
    df = load_sample(sample)
    text = dict(zip(df["id"], df["text"]))
    fps = [r for r in rows if r["pred"] == 1 and r["label"] == 0]
    fns = [r for r in rows if r["pred"] == 0 and r["label"] == 1]
    mal = [r for r in rows if r.get("malformed")]
    def block(title, items):
        out = [f"## {title} ({len(items)})", ""]
        for r in items[:k]:
            t = text.get(r["item_id"], "")[:200].replace("\n", " ")
            out.append(f"- score={fmt(r.get('score'))} raw=`{(r.get('raw') or '')[:60]}` - {t}")
        return out + [""]
    lines = [f"# {arm} on {sample}", "",
             "Filter before using any of these on a slide: no example may target a group, name a real "
             "person or a politician, or use a slur.", ""]
    lines += block("False positives (flagged, gold clean)", sorted(fps, key=lambda r: -(r.get("score") or 0)))
    lines += block("False negatives (missed, gold toxic)", sorted(fns, key=lambda r: (r.get("score") or 0)))
    lines += block("Malformed answers", mal)
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--samples", nargs="+", default=["balanced-2k", "natural-2k"])
    ap.add_argument("--policy", default="open", choices=["open", "closed", "drop"])
    a = ap.parse_args(argv)
    samples = tuple(a.samples)
    summary = collect(a.arm, samples, a.policy)
    write_json(RESULTS / "summary.json", summary)
    md = to_markdown(summary, samples)
    (RESULTS / "summary.md").write_text(md, encoding="utf-8")
    (RESULTS / "errors").mkdir(exist_ok=True)
    for arm in a.arm:
        for s in samples:
            if load_run(s, arm):
                (RESULTS / "errors" / f"{arm_slug(arm)}_{s}.md").write_text(error_examples(arm, s), encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
