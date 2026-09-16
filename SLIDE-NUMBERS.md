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
| small LLM | `[__]` | `[__]` | `[__]` | `[__]` |
| frontier LLM | `[__]` | `[__]` | `[__]` | `[__]` |

natural-2k F1, for the cost slide: regex 0.161 · apc 0.498 · own 0.364

The `+23 points` claim **reproduces**: `scripts/own_cv.py --sample surge-1k` gives
P=0.871 R=0.852 **F1=0.862**, against apc's 0.634 on the same set. 0.862 − 0.634 = +22.8.

Line 158's note resolves to: on the harder disjoint set it's **0.774**, still **+31 points**
above the package (0.774 − 0.462 on balanced-2k).
Line 469's answer to the overfitting question: **0.774**.

## Slide 10 — error examples

Five per arm, filtered under rule 6. Picks and rejections are in `SLIDE-10-EXAMPLES.md`.
Malformed rate for the classical arms is 0% by construction — that column is LLM-only.

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

WARNING: every number on this slide moves. `make obfuscation` rebuilds the set from the new
balanced-2k draw (93 base items), so apc's "original" is 50.5%, not the 91% on the current slide.

## Slide 12 — latency and cost

p50/p95 above. apc cold start: import **2060 ms**, first predict **6 ms**,
max RSS **188 MB**, batch **81,842 items/s**. Concurrency 1, 50 warmup calls, 200 items per arm.

€/1M: `[__]` for every arm — needs `config/prices.toml` (`as_of`, `eur_per_usd`, `[compute]`).
The Anthropic per-token rates are drafted in already.

## Slide 13 — determinism

apc: **0.0% disagreement (0/200)**, 2 runs. regex and own are deterministic by construction.
LLM disagreement: `[__]` — needs the determinism step.

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
