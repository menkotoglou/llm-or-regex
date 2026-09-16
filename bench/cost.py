"""Experiment 2: cost per 1M classifications.

    python -m bench.cost --sample natural-2k --arm apc --arm regex --arm llm:anthropic:<model>

LLM arms:   mean real input/output tokens (from the API's usage field, never estimated)
            x the price in config/prices.toml, which you fill in on the day you run,
            with the date. Prices move; the slide shows the date.
Local arms: instance price per hour / items per hour at the *sequential* rate
            (a web worker classifies one comment per request), and separately at
            batch rate. Both from results/latency/<arm>.json, so run bench.latency first.

Output: results/cost/<arm>.json and a line per arm.
"""
from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

from .arms import arm_slug
from .metrics import load_run, token_means, write_json
from .run import RESULTS, ROOT

PRICES = ROOT / "config" / "prices.toml"


def load_prices() -> dict:
    p = tomllib.loads(PRICES.read_text(encoding="utf-8"))
    if not p.get("as_of") or p.get("eur_per_usd", 0) <= 0:
        raise SystemExit(f"Fill in as_of and eur_per_usd in {PRICES} before computing cost.")
    return p


def llm_cost(sample: str, arm: str, prices: dict) -> dict:
    key = arm.removeprefix("llm:")
    entry = prices.get("llm", {}).get(key)
    if not entry or entry.get("input_per_mtok", 0) <= 0:
        raise SystemExit(f"No price for {key!r} in {PRICES} (section [llm.\"{key}\"]).")
    rows = load_run(sample, arm)
    tin, tout = token_means(rows)
    usd_per_item = tin / 1e6 * entry["input_per_mtok"] + tout / 1e6 * entry["output_per_mtok"]
    usd_per_m = usd_per_item * 1e6
    return {"arm": arm, "sample": sample, "n": len(rows), "mean_tokens_in": tin, "mean_tokens_out": tout,
            "usd_per_1m": usd_per_m, "eur_per_1m": usd_per_m * prices["eur_per_usd"],
            "prices_as_of": prices["as_of"], "price": entry}


def local_cost(arm: str, prices: dict) -> dict:
    comp = prices.get("compute", {})
    if comp.get("usd_per_hour", 0) <= 0:
        raise SystemExit(f"Fill in [compute] usd_per_hour in {PRICES}.")
    lat_path = RESULTS / "latency" / f"{arm_slug(arm)}.json"
    if not lat_path.exists():
        raise SystemExit(f"{lat_path} missing: run `python -m bench.latency --arm {arm}` first.")
    lat = json.loads(lat_path.read_text())
    seq_per_s = lat["sequential_items_per_s"]
    out = {"arm": arm, "instance": comp.get("name"), "usd_per_hour": comp["usd_per_hour"],
           "sequential_items_per_s": seq_per_s, "prices_as_of": prices["as_of"]}
    usd_per_m_seq = comp["usd_per_hour"] / (seq_per_s * 3600) * 1e6
    out["usd_per_1m"] = usd_per_m_seq
    out["eur_per_1m"] = usd_per_m_seq * prices["eur_per_usd"]
    if "batch" in lat:
        b = lat["batch"]["items_per_s"]
        out["batch_items_per_s"] = b
        out["usd_per_1m_batch"] = comp["usd_per_hour"] / (b * 3600) * 1e6
        out["eur_per_1m_batch"] = out["usd_per_1m_batch"] * prices["eur_per_usd"]
    return out


def compute(sample: str, arm: str, prices: dict | None = None) -> dict:
    prices = prices or load_prices()
    return llm_cost(sample, arm, prices) if arm.startswith("llm:") else local_cost(arm, prices)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", default="natural-2k")
    ap.add_argument("--arm", action="append", required=True)
    a = ap.parse_args(argv)
    prices = load_prices()
    for spec in a.arm:
        res = compute(a.sample, spec, prices)
        write_json(RESULTS / "cost" / f"{arm_slug(spec)}.json", res)
        extra = f"  (batch: EUR {res['eur_per_1m_batch']:.2f})" if "eur_per_1m_batch" in res else ""
        print(f"{spec:45s} EUR {res['eur_per_1m']:10.2f} per 1M{extra}")


if __name__ == "__main__":
    main()
