"""Run arms over a sample. Per-item results go to results/<sample>/<arm>/run<k>.jsonl.

    python -m bench.run --sample balanced-2k --arm regex --arm apc
    python -m bench.run --sample natural-2k --arm llm:anthropic:<model> --workers 8
    python -m bench.run --sample balanced-2k --arm llm:openai:<model> --n 200 --runs 3   # determinism

Resumable: items already present in the JSONL are skipped, so a crash or a
rate-limit wall costs nothing. Every run is its own file so run-to-run
disagreement can be measured later.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .arms import arm_slug, build_arm
from .data import load_sample

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"


def result_path(sample: str, arm: str, run: int) -> Path:
    return RESULTS / sample / arm_slug(arm) / f"run{run}.jsonl"


def load_results(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["item_id"]] = r
    return rows


def run_arm(sample: str, arm_spec: str, run: int, n: int | None, workers: int, quiet: bool = False) -> Path:
    df = load_sample(sample)
    if n:
        df = df.head(n)
    out = result_path(sample, arm_spec, run)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = load_results(out)
    todo = [r for r in df.itertuples(index=False) if r.id not in done]
    if not todo:
        if not quiet:
            print(f"[{arm_spec}] {sample} run{run}: all {len(df)} items cached")
        return out

    arm = build_arm(arm_spec)
    t0 = time.perf_counter()
    n_done, n_err, n_mal = 0, 0, 0
    with out.open("a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(arm.predict, r.id, r.text, int(r.label)): r.id for r in todo}
        for fut in as_completed(futures):
            p = fut.result()
            fh.write(p.to_json() + "\n")
            fh.flush()
            n_done += 1
            n_err += p.error is not None
            n_mal += p.malformed
            if not quiet and n_done % 100 == 0:
                el = time.perf_counter() - t0
                print(f"[{arm_spec}] {sample} run{run}: {n_done}/{len(todo)}  "
                      f"errors={n_err} malformed={n_mal}  {el:.0f}s", file=sys.stderr)
    if not quiet:
        print(f"[{arm_spec}] {sample} run{run}: wrote {n_done} items "
              f"(errors={n_err}, malformed={n_mal}) in {time.perf_counter() - t0:.1f}s -> {out}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--arm", action="append", required=True, help="repeatable")
    ap.add_argument("--n", type=int, help="only the first N items of the sample")
    ap.add_argument("--runs", type=int, default=1, help="repeat K times into run0..run{K-1}")
    ap.add_argument("--workers", type=int, default=4, help="use 1 for latency measurements")
    a = ap.parse_args(argv)
    for arm in a.arm:
        for k in range(a.runs):
            run_arm(a.sample, arm, k, a.n, a.workers)


if __name__ == "__main__":
    main()
