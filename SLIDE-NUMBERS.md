# Slide numbers — measured on this machine

Every figure here came from a real run in this repo on macOS 26.5.2 arm64, Python 3.14.3,
sklearn 1.9.0, apc 1.9.0. Nothing is estimated or carried over from the sandbox.
Anything still `[__]` is marked and says what it needs.

Regenerate with: `make local obfuscation && make identity ALL_ARMS="regex apc own:train-4k"`

Sample manifest: `pool_prevalence = 0.0801`, seed 20261012, threshold 0.5.

---

## Slide 9 — the main table  (`results/summary.md`)

| arm | F1 2017 (balanced-2k) | F1 2022 (surge-1k) | p50 | p95 |
|---|---|---|---|---|
| regex | **0.167** | **0.386** | 0.150 ms | 0.633 ms |
| apc | **0.462** | **0.634** | 1.168 ms | 1.210 ms |
| own:train-4k | **0.774** | **0.739** | 0.570 ms | 0.932 ms |
| Haiku 4.5 (small) | **0.588** | **0.959** | 676.0 ms | 930.6 ms |
| Opus 5 (frontier) | **0.666** | **0.977** | 1818.9 ms | 2785.1 ms |

LABEL FLIP — see SLIDE-REWRITES.md. `own:train-4k` beats both LLMs on balanced-2k
(0.774 vs 0.666) and loses to both on surge-1k (0.739 vs 0.977). The slide 9 narrative
as scripted does not survive this; a draft replacement is written up.

natural-2k F1, for the cost slide: regex 0.161 · apc 0.498 · own 0.364

The `+23 points` claim **reproduces**: `scripts/own_cv.py --sample surge-1k` gives
P=0.871 R=0.852 **F1=0.862**, against apc's 0.634 on the same set. 0.862 − 0.634 = +22.8.

Line 158's note resolves to: on the harder disjoint set it's **0.774**, still **+31 points**
above the package (0.774 − 0.462 on balanced-2k).
Line 469's answer to the overfitting question: **0.774**.

## Slide 10 — error examples

Five per arm, filtered under rule 6. Picks and rejections are in `SLIDE-10-EXAMPLES.md`.
MALFORMED IS 0.0% — across all 13,306 LLM calls, four models, two vendors. Script line 175
("In [__] percent of calls the small model didn't return JSON") did not reproduce. All three
malformed policies give byte-identical tables. Replacement argument in SLIDE-REWRITES.md.

## Slide 10b — identity false positives  (`results/identity.md`, out of 5)

| identity | regex | apc | own:surge-1k | own:train-4k |
|---|---|---|---|---|
| queer | 0/5 | **4/5** | 0/5 | 0/5 |
| gay | 0/5 | **2/5** | 0/5 | **3/5** |
| white | 0/5 | 0/5 | 0/5 | **4/5** |
| Muslim | 0/5 | 0/5 | 0/5 | **4/5** |
| Black | 0/5 | 0/5 | **1/5** | **3/5** |
| transgender · cisgender · bisexual | 0/5 | 0/5 | 0/5 | **3/5** each |
| **total flagged / 115** | 0 | 6 | 1 | **30 (26%)** |

Haiku 4.5 and Opus 5: **0/115 each**. Both LLM arms are clean on every identity term.

DECISION OUTSTANDING: the deck currently shows `own:surge-1k` (1/115). `own:train-4k`,
the arm benchmarked everywhere else, is at 30/115.

## Slide 11 — obfuscation recall %  (`results/obfuscation.md`)

| transform | regex | apc | own:train-4k |
|---|---|---|---|
| original | 100.0 | 50.5 | 74.2 |
| l33t (`fvck`/`$h17`) | 1.1 | 11.8 | 60.2 |
| spaced (`f u c k`) | 0.0 | 11.8 | 59.1 |
| homoglyph (Cyrillic а/е/о) | 8.6 | 14.0 | 60.2 |
| asterisk (`f**k`) | 1.1 | 11.8 | 61.3 |
| concatenated (`youfucking`) | 5.4 | 11.8 | 65.6 |

LLM columns (recall %): Haiku original 50.5 / l33t 57.0 / spaced 54.8 / homoglyph 53.8 /
asterisk 59.1 / concatenated 54.8. Opus 5: 59.1 / 59.1 / 55.9 / 55.9 / 59.1 / 60.2.
They are FLAT — the LLMs do not collapse under obfuscation. That is the slide.

WARNING: every number on this slide moves. `make obfuscation` rebuilds the set from the new
balanced-2k draw (93 base items), so apc's "original" is 50.5%, not the 91% on the current slide.

## Slide 12 — latency and cost

p50/p95 above. apc cold start: import **2060 ms**, first predict **6 ms**,
max RSS **188 MB**, batch **81,842 items/s**. Concurrency 1, 50 warmup calls, 200 items per arm.

€/1M: `[__]` for every arm — needs `config/prices.toml` (`as_of`, `eur_per_usd`, `[compute]`).
The Anthropic per-token rates are drafted in already.

## Slide 13 — determinism

apc: **0.0% disagreement (0/200)**, 2 runs. regex and own are deterministic by construction.
LLM disagreement, 200 items x 3 runs: **Haiku 4.5 = 6.5% (13/200)**, **Opus 5 = 1.5% (3/200)**.
The cheap model is 4x less stable than the frontier one. Both at default sampling.

REWRITE REQUIRED. The slide says "temperature 0". That is not reachable:

- `anthropic` 1.6.0 has removed `temperature`, `top_p` and `top_k` from `messages.create()`
  entirely — a client-side TypeError, never a network call.
- Underneath the SDK the API disagrees by model: reaching around it with
  `extra_body={"temperature": 0}`, Haiku 4.5 **accepts**, Opus 5 returns
  `400 — temperature is deprecated for this model`.
- `openai` 3.14.1 still has `temperature` in its signature. Same year, opposite decision.

Both arms were therefore run with no temperature parameter, at each model's default sampling.
Each row records this: `meta.temperature_ok = false`.

Suggested line: *"I wanted to run this at temperature zero. I couldn't. The SDK deleted the
parameter, and underneath it the frontier model rejects it outright — while the other vendor's
SDK still has it. The knob you pin determinism with is itself a rented, moving part."*

## Slides 16, 21 — not run

Slide 16 (extraction bench): `extract/` was never written. Six placeholders, needs a decision.
Slide 21 (cascade): needs the LLM arms, then `make cascade`.

## Provenance

commit `[fill after the run]` · `git rev-parse --short HEAD`

---

# FINAL — all four LLM arms, costs included  (commit 732c848)

22,688 scored LLM items. **0 malformed. 0 unresolved errors.** Four models, two vendors.

## Slide 9 / 12 — the complete table

| arm | F1 2017 | F1 natural | F1 2022 | p50 | p99 | €/1M | disagree |
|---|---|---|---|---|---|---|---|
| regex | 0.167 | 0.161 | 0.386 | 0.15 ms | 0.70 ms | 0.00 | — |
| apc | 0.462 | 0.498 | 0.634 | 1.17 ms | 1.27 ms | 0.01 | 0.0% |
| own:train-4k | **0.774** | 0.364 | 0.739 | 0.57 ms | 0.99 ms | 0.00 | — |
| gpt-5.4-mini | 0.709 | 0.415 | 0.968 | 624 ms | 990 ms | 148.52 | 5.5% |
| Haiku 4.5 | 0.588 | 0.447 | 0.959 | 676 ms | 1667 ms | 208.55 | 6.5% |
| Opus 5 | 0.666 | 0.467 | 0.977 | 1819 ms | 3608 ms | 1398.79 | 1.5% |
| gpt-6-astra | 0.749 | 0.407 | **0.989** | 1652 ms | 4912 ms | 2195.05 | 4.5% |

Costs: natural-2k (8% toxic), real token counts, prices as_of 2026-09-17,
eur_per_usd 0.8668 (ECB 16 Sep fixing), compute = DigitalOcean 1 vCPU / 2 GiB @ $0.01786/h.

Headline ratios: **apc €0.01 vs astra €2,195 = ~220,000x.**
**astra costs 14.8x gpt-5.4-mini and buys +0.021 F1**, with a 4.9x worse p99.

## Slide 10b — identity FPs / 115

regex 0 · apc 6 · own:surge-1k 1 · **own:train-4k 30** · all four LLM arms **0**.

## Slide 11 — obfuscation recall %

| transform | regex | apc | own | Haiku | Opus 5 | mini | astra |
|---|---|---|---|---|---|---|---|
| original | 100.0 | 50.5 | 74.2 | 50.5 | 59.1 | 62.4 | 66.7 |
| l33t | 1.1 | 11.8 | 60.2 | 57.0 | 59.1 | 64.5 | 72.0 |
| spaced | 0.0 | 11.8 | 59.1 | 54.8 | 55.9 | 65.6 | 69.9 |
| homoglyph | 8.6 | 14.0 | 60.2 | 53.8 | 55.9 | 66.7 | 68.8 |
| asterisk | 1.1 | 11.8 | 61.3 | 59.1 | 59.1 | 67.7 | 73.1 |
| concatenated | 5.4 | 11.8 | 65.6 | 54.8 | 60.2 | 66.7 | 66.7 |

The LLM columns are FLAT. The OpenAI pair score HIGHER on obfuscated text than on clean.

## Slide 21 — cascade (router = own:train-4k, natural-2k)

| LLM | alone F1 / €1M | best cascade F1 | LO/HI | traffic to LLM | €1M |
|---|---|---|---|---|---|
| Haiku 4.5 | 0.447 / 209 | 0.486 | 0.20/0.80 | 63.8% | 133 |
| Opus 5 | 0.467 / 1399 | 0.482 | 0.30/0.95 | 48.5% | 679 |
| gpt-5.4-mini | 0.415 / 149 | **0.457** | 0.30/0.80 | 44.5% | **66** |
| gpt-6-astra | 0.407 / 2195 | 0.437 | 0.30/0.95 | 48.5% | 1066 |

Every cascade beats its LLM alone on F1 AND roughly halves cost. Routing usually trades
accuracy for money; here it buys both, because the router filters easy negatives that were
destroying LLM precision at natural prevalence.

## Slide 13 — determinism, four models

Opus 5 1.5% · astra 4.5% · gpt-5.4-mini 5.5% · Haiku 6.5%. All at default sampling;
temperature 0 was not reachable (see the rewrite note above).
