"""Experiment 8: the hybrid cascade, computed offline from existing per-item results.

    python -m bench.cascade --sample natural-2k --llm llm:anthropic:<model> --router own:train-4k

Routing rule (this is the code that goes on the Section 5 slide):

    if regex hits:               toxic          # cheap, auditable, catches the obvious
    elif router_prob >= hi:      toxic          # the model is sure
    elif router_prob <= lo:      clean          # the model is sure
    else:                        ask the LLM    # only the uncertain band pays for tokens

Sweeps (lo, hi) and reports, per setting: share of traffic reaching the LLM,
precision/recall/F1 of the *blended* answer, and blended cost per 1M
(share_to_llm x LLM cost + router cost). Needs run0 of regex, the router and the
LLM arm on the same sample, plus bench.cost for those arms.

The router defaults to own:train-4k, not apc: apc's misses score ~0.005, so they
never land in its uncertain band. Confidence routing only works when the cheap
model answers the same question as the product.

Output: results/cascade/<sample>_<llm>.json and .md
"""
from __future__ import annotations

import argparse
import json

from .arms import arm_slug
from .metrics import load_run, prf, write_json
from .run import RESULTS

LO_GRID = (0.02, 0.05, 0.10, 0.15, 0.20, 0.30)
HI_GRID = (0.70, 0.80, 0.90, 0.95, 0.99)


def route(regex_pred: int, router_prob: float, llm_pred, lo: float, hi: float) -> tuple[object, str]:
    if regex_pred == 1:
        return 1, "regex"
    if router_prob >= hi:
        return 1, "router"
    if router_prob <= lo:
        return 0, "router"
    return llm_pred, "llm"


def evaluate(sample: str, llm: str, router: str = "own:train-4k", policy: str = "open") -> dict:
    rx = {r["item_id"]: r for r in load_run(sample, "regex")}
    rt = {r["item_id"]: r for r in load_run(sample, router)}
    lm = {r["item_id"]: r for r in load_run(sample, llm)}
    ids = [i for i in rt if i in rx and i in lm]
    if not ids:
        raise SystemExit(f"need run0 of regex, {router} and {llm} on {sample} first")

    def cost_of(arm):
        p = RESULTS / "cost" / f"{arm_slug(arm)}.json"
        return json.loads(p.read_text())["eur_per_1m"] if p.exists() else None
    c_llm, c_rt = cost_of(llm), cost_of(router)

    baselines = {name: prf(list(d.values()), policy) for name, d in (("regex", rx), (router, rt), (llm, lm))}
    grid = []
    for lo in LO_GRID:
        for hi in HI_GRID:
            rows, routes = [], {"regex": 0, "router": 0, "llm": 0}
            for i in ids:
                pred, via = route(rx[i]["pred"], rt[i]["score"], lm[i]["pred"], lo, hi)
                routes[via] += 1
                rows.append({"item_id": i, "label": rt[i]["label"], "pred": pred,
                             "malformed": via == "llm" and lm[i].get("malformed", False)})
            m = prf(rows, policy)
            share = routes["llm"] / len(ids)
            blended = (share * c_llm + c_rt) if (c_llm is not None and c_rt is not None) else None
            grid.append({"lo": lo, "hi": hi, "share_to_llm": share, "routes": routes,
                         "precision": m["precision"], "recall": m["recall"], "f1": m["f1"],
                         "eur_per_1m": blended})
    return {"sample": sample, "llm": llm, "router": router, "n": len(ids), "policy": policy,
            "cost_llm_eur_per_1m": c_llm, "cost_router_eur_per_1m": c_rt,
            "baselines": baselines, "grid": grid}


def to_markdown(res: dict) -> str:
    b = res["baselines"]
    lines = [f"# Cascade on {res['sample']} (n={res['n']}, router = {res['router']}, LLM = {res['llm']})", "",
             "| arm | P | R | F1 | EUR/1M |", "|---|---|---|---|---|"]
    for name, m in b.items():
        cost = res["cost_llm_eur_per_1m"] if name == res["llm"] else (
            res["cost_router_eur_per_1m"] if name == res["router"] else 0)
        cost_s = "" if cost is None else f"{cost:.2f}"
        lines.append(f"| {name} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {cost_s} |")
    lines += ["", "| lo | hi | to LLM | P | R | F1 | EUR/1M |", "|---|---|---|---|---|---|---|"]
    for g in res["grid"]:
        cost_s = "" if g["eur_per_1m"] is None else f"{g['eur_per_1m']:.2f}"
        lines.append(f"| {g['lo']:.2f} | {g['hi']:.2f} | {g['share_to_llm']:.1%} | {g['precision']:.3f} | "
                     f"{g['recall']:.3f} | {g['f1']:.3f} | {cost_s} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", default="natural-2k")
    ap.add_argument("--llm", required=True, help="the LLM arm spec used for the uncertain band")
    ap.add_argument("--router", default="own:train-4k", help="the cheap arm that routes")
    ap.add_argument("--policy", default="open", choices=["open", "closed", "drop"])
    a = ap.parse_args(argv)
    res = evaluate(a.sample, a.llm, a.router, a.policy)
    stem = f"{a.sample}_{arm_slug(a.llm)}"
    write_json(RESULTS / "cascade" / f"{stem}.json", res)
    md = to_markdown(res)
    (RESULTS / "cascade" / f"{stem}.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
