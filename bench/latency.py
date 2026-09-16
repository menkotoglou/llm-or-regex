"""Experiment 3: latency.

    python -m bench.latency --sample balanced-2k --arm regex --arm apc --arm llm:anthropic:<model>

Hygiene, so the numbers survive Q&A:
  - concurrency 1 (a web request classifies one comment at a time)
  - 50 warmup calls that are thrown away
  - the same 200 items for every arm
  - LLM latency includes the network from wherever you run it; the slide says where
  - apc gets three extra numbers a web app cares about: batch throughput,
    cold start (import + first predict in a fresh interpreter) and resident memory

Output: results/latency/<arm>.json
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from .arms import APCArm, arm_slug, build_arm
from .data import load_sample
from .metrics import percentiles, write_json
from .run import RESULTS

COLD_START_SNIPPET = r"""
import resource, sys, time
t0 = time.perf_counter()
from profanity_check import predict_prob
t_import = time.perf_counter() - t0
t1 = time.perf_counter()
predict_prob(["warm up the model"])
t_first = time.perf_counter() - t1
rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
rss_mb = rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024
print(f"{t_import:.4f} {t_first:.4f} {rss_mb:.1f}")
"""


def cold_start(reps: int = 5) -> dict:
    imports, firsts, rss = [], [], []
    for _ in range(reps):
        out = subprocess.run([sys.executable, "-c", COLD_START_SNIPPET], capture_output=True, text=True, check=True)
        a, b, c = map(float, out.stdout.split())
        imports.append(a * 1000); firsts.append(b * 1000); rss.append(c)
    return {"reps": reps, "import_ms": percentiles(imports), "first_predict_ms": percentiles(firsts),
            "max_rss_mb": percentiles(rss)}


def batch_throughput(arm: APCArm, texts: list[str], batch: int = 1000, reps: int = 5) -> dict:
    chunk = (texts * (batch // len(texts) + 1))[:batch]
    arm.predict_batch(chunk[:50])  # warm
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        arm.predict_batch(chunk)
        times.append(time.perf_counter() - t0)
    best = min(times)
    return {"batch": batch, "reps": reps, "best_s": best, "items_per_s": batch / best}


def measure(sample: str, arm_spec: str, n: int, warmup: int) -> dict:
    df = load_sample(sample).head(n + warmup)
    arm = build_arm(arm_spec)
    rows = list(df.itertuples(index=False))
    for r in rows[:warmup]:
        arm.predict(r.id, r.text, int(r.label))
    lat, errors, attempts = [], 0, []
    t0 = time.perf_counter()
    for r in rows[warmup:warmup + n]:
        p = arm.predict(r.id, r.text, int(r.label))
        if p.error:
            errors += 1
            continue
        lat.append(p.latency_ms)
        attempts.append(p.attempts)
    wall = time.perf_counter() - t0
    out = {
        "arm": arm_spec, "sample": sample, "n": n, "warmup": warmup, "errors": errors,
        "latency_ms": percentiles(lat),
        "retries_total": sum(a - 1 for a in attempts),
        "sequential_items_per_s": (len(lat) / wall) if wall else None,
        "machine": {"platform": platform.platform(), "python": platform.python_version(),
                    "cpu": platform.processor() or platform.machine()},
        "measured_at": time.strftime("%Y-%m-%d %H:%M %Z"),
    }
    if isinstance(arm, APCArm):
        texts = [r.text for r in rows[:200]]
        out["batch"] = batch_throughput(arm, texts)
        out["cold_start"] = cold_start()
        out["version"] = arm.version
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", default="balanced-2k")
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--warmup", type=int, default=50)
    a = ap.parse_args(argv)
    for spec in a.arm:
        res = measure(a.sample, spec, a.n, a.warmup)
        write_json(RESULTS / "latency" / f"{arm_slug(spec)}.json", res)
        l = res["latency_ms"]
        print(f"{spec:45s} p50={l.get('p50', 0):9.2f}ms  p95={l.get('p95', 0):9.2f}ms  "
              f"p99={l.get('p99', 0):9.2f}ms  errors={res['errors']}")
        if "cold_start" in res:
            c = res["cold_start"]
            print(f"{'':45s} cold start import p50={c['import_ms']['p50']:.0f}ms  "
                  f"first predict p50={c['first_predict_ms']['p50']:.0f}ms  "
                  f"RSS p50={c['max_rss_mb']['p50']:.0f}MB  batch={res['batch']['items_per_s']:.0f} items/s")


if __name__ == "__main__":
    main()
