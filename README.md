# LLM or Regex?

The benchmark behind **LLM or Regex? Choosing Tools for Text Problems in Python**, a talk at
[PyCon Greece 2026](https://2026.pycon.gr/en/program/schedule/) (Athens, 12 October 2026).

Three kinds of tool for the same text problem, measured side by side:

- **a regex**: a banned-word list;
- **classical ML**: [alt-profanity-check](https://pypi.org/project/alt-profanity-check/), and a small
  scikit-learn classifier trained on the task's own labels;
- **LLMs**: four models from two vendors, one prompt.

The main task is comment moderation. A small extraction task (booking requests → form fields)
checks that the conclusions transfer. The talk scores every tool on six questions: what does
"right" mean, what happens when it's wrong, can the user wait, what does it cost, how does it age,
and can you explain a decision. Every figure in the talk comes from the per-item rows committed in
[`results/`](results/), and one command rebuilds every table from them.

## Results

| tool | F1 · 2017 news, balanced | F1 · 2017 news, 8% toxic | F1 · 2022 social media | median latency | € per 1M comments | answers changed on rerun |
|---|---:|---:|---:|---:|---:|---:|
| regex (LDNOOBW list) | 0.167 | 0.161 | 0.386 | 0.15 ms | 0.00 | — |
| alt-profanity-check 1.9.0 | 0.462 | 0.498 | 0.634 | 1.2 ms | 0.01 | 0.0% |
| own classifier (tf-idf + LR, 4k labels) | **0.774** | 0.364 | 0.739 | 0.6 ms | 0.00 | — |
| claude-haiku-4-5 | 0.588 | 0.447 | 0.959 | 676 ms | 208.55 | 6.5% |
| claude-opus-5 | 0.666 | **0.467** | 0.977 | 1,819 ms | 1,398.79 | 1.5% |
| gpt-5.4-mini | 0.709 | 0.415 | 0.968 | 624 ms | 148.52 | 5.5% |
| gpt-6-astra | 0.749 | 0.407 | **0.989** | 1,652 ms | 2,195.05 | 4.5% |

From [`results/summary.md`](results/summary.md). Latency is one call at a time from the author's
laptop (macOS, arm64), network included. Cost is at natural prevalence (8% toxic) from the API's
real token counts, at prices from 17 September 2026 ([`config/prices.toml`](config/prices.toml)); the
local tools are priced on a small 1 vCPU cloud server. "Answers changed" is the same 200 comments
asked three times (twice for alt-profanity-check).

What it shows:

- **The winner depends on who wrote the answers.** Trained on 2017 crowd labels, a 20-line
  classifier beats every LLM on more comments labelled the same way (0.774 against 0.588–0.749),
  and loses to all of them on 2022 social media (0.739 against 0.959–0.989).
- **Each tool fails differently.** The word list fails on words. alt-profanity-check answers "is
  there profanity?" when the product asks "is this hostile?". The LLMs never broke the output
  format (0 malformed answers in 24,316 rows), but they change a few answers in every hundred when
  asked again, even the one model that accepted temperature 0.
- **The failure that silences people.** Of 115 friendly sentences that mention an identity,
  alt-profanity-check flags 6 ("queer" 4 of 5, "gay" 2 of 5), the classifier trained on 2017 labels
  flags 30, and the word list and all four LLMs flag none ([`results/identity.md`](results/identity.md)).
- **Spelling tricks** (`f u c k`, `f**k`, lookalike letters) take the word list from 100% recall to
  under 9%, and alt-profanity-check from 50% to about 12–14%. The LLMs don't notice
  ([`results/obfuscation.md`](results/obfuscation.md)).
- **Speed and money** are far apart. At 100,000 comments a day the local tools cost effectively
  nothing a month, the cheapest LLM about €450 and the most expensive about €6,600.
- **Chaining wins.** When a classifier trained on the task's labels decides only when it's sure,
  and only the unsure band goes to the LLM, the result is cheaper *and* more accurate than the LLM
  alone, for all four LLMs ([`results/cascade/`](results/cascade/)). alt-profanity-check can't be that
  first step: when it is wrong, it is confidently wrong, so its mistakes never reach the LLM.
- **Extraction.** On fields with a pattern (time, party size) the regex is perfect; on fields that
  need meaning the LLMs win; and gpt-5.4-mini invented a location in 6% of the requests that didn't
  mention one ([`results/extraction.md`](results/extraction.md)).

These are results for these datasets. The point of the repo is that you can run the same
comparison on your own traffic.

## The arms

| arm | what it is |
|---|---|
| `regex` | the LDNOOBW English list (403 entries), case-insensitive, word boundaries |
| `apc` | alt-profanity-check 1.9.0 (bag of words, linear SVM), threshold 0.5. 1.9.1 ships the same weights and scores identically |
| `own:<sample>` | tf-idf (word and character n-grams) + logistic regression trained on that sample: `train-4k` everywhere, disjoint from the test sets; `surge-1k` for one identity comparison |
| `llm:<provider>:<model>` | one prompt ([`prompts/moderation.txt`](prompts/moderation.txt)), a JSON answer, at most 256 output tokens |
| `llm:fake:any` | an offline stand-in used by `make dryrun` |

The four LLM arms and the settings each one actually accepted (recorded per row under `meta`):

| arm | settings |
|---|---|
| `llm:anthropic:claude-haiku-4-5-20251001` | default sampling (the SDK no longer takes `temperature`), thinking off |
| `llm:anthropic:claude-opus-5` | default sampling (the model rejects `temperature`), thinking off |
| `llm:openai:gpt-5.4-mini` | `temperature=0`, `reasoning_effort="none"` |
| `llm:openai:gpt-6-astra` | default sampling (the model rejects `temperature`), `reasoning_effort="low"` (it rejects `"none"`) |

## Data

Civil Comments (2017 news comments, CC0), the Surge AI toxicity set (2022 social media, MIT), the
LDNOOBW word list (CC BY 4.0), and a few small sets generated here: identity sentences, spelling
tricks and booking requests. Details, counts and licences: [`data/README.md`](data/README.md).
Content warning: these are toxicity datasets, and some rows are offensive by design.

## Reproduce

Rebuild every table from the committed per-item rows. This is offline, free, and takes a few
seconds:

```sh
make setup      # .venv + requirements.txt; for the exact versions: .venv/bin/pip install -r requirements-lock.txt
make tables     # cost, chains, summary, identity and obfuscation tables
```

The only differences from the committed tables should be the timestamp and commit hash in
`results/summary.md`. The extraction table is the exception: its per-item outputs were not stored,
so it needs the LLM arms again.

Re-run the experiments:

```sh
make dryrun                                        # every module with a fake LLM arm: no network, no money
make wordlist samples                              # network: re-fetch the word list, redraw the samples (both committed)
make local obfuscation                             # the free arms on the 2017 samples and the spelling tricks
make identity ALL_ARMS="regex apc own:train-4k"    # the identity sentences, free arms only

# The LLM arms cost money: about 6,500 calls per model for everything.
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=...
make llm handlabeled extraction
make tables
```

Runs are resumable. Items already present in `results/<sample>/<arm>/run<k>.jsonl` are skipped, so
a crash or a rate limit costs nothing; lower `WORKERS` and run the same command again. Latency and
extraction are measured fresh every time. To try other models, set `LLM_ARMS`, and add their prices
(dated, from the providers' pricing pages) to `config/prices.toml` before `make cost`.

## Layout

```
bench/          the harness: arms, runs, metrics, latency, determinism, cost, chains, report, extraction
scripts/        data generators (identity, obfuscation, extraction), table scripts, word-list fetch
prompts/        the moderation and extraction prompts, verbatim
config/         dated prices and the compute assumption for the local arms
data/           samples and hand-made sets, with sources and licences
results/        per-item rows and every table built from them; see results/README.md
notes/          working notes from preparing the talk
CLAUDE.md       rules for coding agents working in this repo (never invent a number; ask before spending)
```

## Caveats

- The LLMs have very likely seen Civil Comments and the Surge AI set during pretraining. That
  favours them.
- Latency depends on where you run from. These numbers include the author's home network.
- Prices change. The table in `config/prices.toml` carries its date.
- The chain's best thresholds were picked on the same data they were scored on. A wide range of
  thresholds (10 to 27 of the 30 tried, depending on the LLM) beats the LLM alone on both cost
  and F1.
- The extraction set is generated from templates, not collected.

## Licence

Code: [MIT](LICENSE). Data: see [`data/README.md`](data/README.md) (CC0, MIT and CC BY 4.0 sources).
