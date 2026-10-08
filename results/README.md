# Results

Everything here was produced by the code in this repo, on one machine (macOS 26.5 arm64,
Python 3.14.3), between 16 and 17 September 2026. Treat it as append-only evidence: a surprising
number gets checked against the per-item rows, not edited.

## Per-item rows (the source of truth)

`<sample>/<arm>/run<k>.jsonl`, one JSON object per item:

| field | meaning |
|---|---|
| `item_id` | row id in the sample's CSV under `data/` |
| `label`, `pred` | gold label and the arm's verdict (1 = toxic) |
| `score` | the arm's probability, where it has one (regex: 0 or 1; LLMs: none) |
| `latency_ms`, `tokens_in`, `tokens_out` | per call; tokens are the API's own counts |
| `malformed`, `error`, `attempts`, `raw` | what came back and how many tries it took |
| `meta` | package version, or the LLM settings that were actually accepted |

`run1`, `run2` exist where an arm was asked the same items again (the determinism check).
Runs are resumable: items already present are skipped, errored rows are kept and retried.

## Tables built from those rows

| file | built by | what it shows |
|---|---|---|
| `summary.md`, `summary.json` | `bench.report` | P/R/F1 on the three samples, latency, € per 1M, malformed and run-to-run disagreement, per arm |
| `errors/<arm>_<sample>.md` | `bench.report` | the most confident false positives and false negatives, for picking examples |
| `latency/<arm>.json` | `bench.latency` | p50/p95/p99 at concurrency 1 after 50 warm-up calls; for alt-profanity-check also cold start, RSS and batch throughput |
| `cost/<arm>.json` | `bench.cost` | € per 1M at natural prevalence, from real token counts × `config/prices.toml` (prices as of 17 Sep 2026) |
| `determinism/<arm>.json` | `bench.determinism` | the same 200 items asked 3 times: how many answers changed |
| `cascade/natural-2k_<llm>.md` | `bench.cascade` | the chain with `own:train-4k` in the middle (it decides when sure, the LLM only gets the unsure band): F1 and € for every LO/HI pair |
| `cascade/<sample>_<llm>__router_apc.md` | `bench.cascade --router apc` | the same chain with alt-profanity-check in the middle, on natural-2k and surge-1k (the talk's chain) |
| `identity.md` | `scripts/identity_table.py` | share of the 5 friendly sentences per identity that each arm flagged |
| `obfuscation.md` | `scripts/obfuscation_table.py` | recall per spelling trick |
| `extraction.md`, `extraction/*.json` | `bench.extract` | per-field accuracy and invention rate on the booking requests (aggregates only: per-item extraction outputs were not stored) |

`make tables` rebuilds every table except the extraction one from the committed rows, offline and
for free. The extraction table needs the LLM arms to be run again.

`RESULTS-2026-09-02.md` is an early write-up from a sandbox run, superseded by everything above
(its regex and alt-profanity-check rows were re-run on the measuring machine and reproduced). It is
kept as a record, not as a source.

alt-profanity-check 1.9.1 (released after these runs) ships the same weights as 1.9.0, re-saved for
scikit-learn 1.9.1: rescoring all 6,988 items it touches here changes no score by more than 4e-16
and no prediction.
