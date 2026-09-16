# LLM or Regex? — benchmark harness

Numbers behind the PyCon Greece 2026 talk *LLM or Regex? Choosing Tools for Text Problems in Python*.
Five arms, one interface, six decision axes. Everything here is reproducible from one command per
experiment; the per-item outputs (`results/**/run*.jsonl`) are what the slides are built from.

Read `CLAUDE.md` before running anything with an agent. `RUNBOOK.md` has the step order.

| arm | what it is |
|---|---|
| `regex` | LDNOOBW English banned-word list, word-boundary match, case-insensitive |
| `apc` | [`alt-profanity-check`](https://pypi.org/project/alt-profanity-check/) 1.9.0 — bag of words + LinearSVC, threshold 0.5 |
| `own:<train-sample>` | tf-idf (word + char n-grams) + logistic regression trained on *your* labels (`train-4k`, disjoint from the eval samples). The "you have a thousand labels" arm |
| `llm:<provider>:<model>` | one prompt (`prompts/moderation.txt`), JSON answer, temperature 0. Run it once for a small model and once for a frontier model |

## Datasets

[Civil Comments](https://huggingface.co/datasets/google/civil_comments) (Jigsaw Unintended Bias, 2019), gold = `toxicity >= 0.5`.

**Not** the Jigsaw Toxic Comment (Wikipedia) set: `alt-profanity-check` was trained on it, so evaluating
there would be leakage in its favour. The LLMs have very likely seen both corpora in pretraining; that
asymmetry is stated on the slide, and `data/handlabeled/ood.csv` is the sanity check.

Three fixed samples, seed `20261012`, written to `data/samples/` and committed:

- `balanced-2k` — 1,000 toxic / 1,000 clean → accuracy comparison
- `natural-2k` — 2,000 at natural prevalence (~8% toxic) → cost and precision, i.e. what production looks like
- `train-4k` — 2,000 / 2,000, disjoint from both → training data for `own:train-4k`

Also included: `data/handlabeled/surge-1k.csv` (Surge AI toxicity, 2022, 1,000 items, held out from apc)
and the generated `obfuscation.csv` and `identity.csv`. Sandbox results for the non-LLM arms and the
write-up are in `results/`.

## Run

```sh
make setup wordlist samples      # once
make dryrun                      # every module, fake LLM arm, no network, no money
make local obfuscation           # experiments 1-3 and 7 for regex + apc + own, free
make identity ALL_ARMS="regex apc own:train-4k"

export ANTHROPIC_API_KEY=... OPENAI_API_KEY=...
make llm LLM_SMALL=llm:anthropic:<small> LLM_FRONTIER=llm:anthropic:<frontier>   # spends money
make handlabeled LLM_SMALL=... LLM_FRONTIER=...
# fill config/prices.toml (dated), then:
make cost cascade report LLM_SMALL=... LLM_FRONTIER=...
```

Every run is resumable: items already in `results/<sample>/<arm>/run<k>.jsonl` are skipped.

## Experiments → axes → slides

| # | command | measures | axis |
|---|---|---|---|
| 1 | `bench.run --sample balanced-2k` | P / R / F1 per arm + the worst errors (`results/errors/`) | accuracy ceiling, failure mode |
| 2 | `bench.run --sample natural-2k` + `bench.cost` | € per 1M classifications, precision at natural prevalence | cost |
| 3 | `bench.latency` | p50/p95/p99 at concurrency 1, 50 warmup; apc batch throughput, cold start, RSS | latency, ops reality |
| 4 | `bench.determinism` | same 200 items × 3 runs at temperature 0: disagreement %, malformed % | drift, failure mode |
| 5 | `bench.run --sample ood` | hand-labelled out-of-distribution set, see `data/handlabeled/README.md` | contamination check |
| 7 | `make obfuscation` | every word-list match l33t / spaced / homoglyph / asterisk / concatenated, recall per transform | failure mode |
| 9 | `make identity` | 115 innocuous sentences mentioning an identity, all clean; false-positive rate per identity per arm | failure mode, the one that silences people |
| 8 | `bench.cascade` | regex → router confidence band → LLM only for the uncertain middle; traffic share to LLM, blended F1, blended € | the hybrid, Section 5 |

`bench.report` writes `results/summary.md`: the one table that becomes the central slide.

## Hygiene that survives Q&A

- One machine, stated on the slide (`results/latency/*.json` records platform and time).
- LLM latency includes the network from the measuring machine. Say where you measured from.
- Costs come from the API's real token counts × a dated price table (`config/prices.toml`). Never estimates.
- Malformed LLM output is a first-class result, not an exclusion: `--policy open|closed|drop` shows how
  each choice moves precision and recall. That is the "what does your app do when the model returns prose?" slide.
- `apc` threshold is the library default (0.5); the cascade sweeps the confidence band, not the threshold.
- The cascade router is `own`, not `apc`: apc's misses score ~0.005, so they never reach its uncertain band.
- Seeds, sample indices, prompt and package versions are committed. The summary carries the commit hash.

MIT.
