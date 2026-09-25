# Two slides the measurements broke, and drafts to replace them

Both problems are good news: the replacement arguments are stronger than the originals,
and unlike the originals they are backed by numbers from this repo.

---

# Slide 9 — the label-flip

## What broke

The script says: *"the row I want you to look at is the third one … gets 0.86. That's
twenty-three points above the pretrained package."* That still holds against `apc`.
It no longer holds against the LLMs:

| | balanced-2k (Civil Comments, 2017 crowd labels) | surge-1k (your 2022 hand labels) |
|---|---|---|
| own:train-4k | **0.774** | 0.739 |
| Haiku 4.5 | 0.588 | **0.959** |
| Opus 5 | 0.666 | **0.977** |

Your classifier wins by 11 points on one set. The frontier model wins by 24 points on the
other. Same arms, same code, opposite conclusions.

## Draft A — keep the thesis, use the flip as the proof  (recommended)

The thesis was never "small models beat big ones". It was **"the accuracy ceiling is about
whether your labels match your question."** The flip is that claim's strongest possible evidence:

> Look at these two columns. On the left, my twenty-line classifier beats a frontier model by
> eleven points. On the right, the same frontier model beats my classifier by twenty-four.
>
> Nothing about the models changed. What changed is whose definition of "toxic" we scored against.
>
> On the left I'm scoring against Civil Comments' crowd labels from 2017 — and my classifier was
> trained on Civil Comments' crowd labels from 2017. Of course it wins. It learned the label-generating
> process, not the concept.
>
> On the right I'm scoring against my labels. The ones where I decided what my product means by toxic.
> And the LLM wins, because I wrote that definition into the prompt — in English, in four sentences.
>
> So the real question isn't "which model is smarter". Both arms are doing the same thing: agreeing
> with whoever wrote the labels. The question is whose definition you're buying, and how you'd know.

Then the decision axes become the ones that don't flip: **1,500× latency** (1819 ms vs 1.17 ms),
cost, and determinism.

## Draft B — concede accuracy, pivot to the other three axes

Shorter, more honest-feeling, weaker:

> I'll be direct: on the set that matters to my product, the LLM wins on accuracy and it isn't
> close. 0.977 against 0.739. If accuracy were the only axis, this talk would be one slide long.
> It isn't, and the rest of this talk is the other three axes — latency, cost, and whether the
> answer is the same tomorrow.

Draft B gives up the most interesting finding in the dataset. Use it only if you're short on time.

---

# Slide 10 — the contract argument

## What broke

The script says: *"In `[__]` percent of calls the small model didn't return JSON. It returned a
sentence."* Measured across **13,306 calls on four models from two vendors: 0.0%.** Not one.
All three malformed policies (`open` / `closed` / `drop`) produce byte-identical tables.

The premise is false in 2026. Modern models return the JSON you asked for.

## Draft — the contract does break, just not where you were looking

Everything below happened in this repo in one afternoon, and every line is in git:

> I built this harness expecting to show you malformed output. Thirteen thousand calls, four models,
> two vendors — I got zero. Not one prose answer. That argument is dead, and I'm glad.
>
> Here's what actually broke.
>
> `temperature=0` — the line in my code that pins determinism. The Anthropic SDK **removed the
> parameter**. Not deprecated, removed from the function signature. A TypeError, before any network
> call. Underneath it, the API disagrees with itself by model: Haiku still accepts temperature,
> Opus 5 returns *"temperature is deprecated for this model"*. The OpenAI SDK still has it.
>
> `max_tokens` is not `max_tokens` any more — reasoning models want `max_completion_tokens`, and
> tell you so with a 400.
>
> I asked one model for `reasoning_effort: "none"`. Supported values: low, medium, high, xhigh.
> My fallback turned reasoning *off*, which silently turned it all the way *up*.
>
> And my favourite. I capped output at 24 tokens, because `{"toxic": true}` is nine. One model
> spends up to 53 tokens thinking first. It hit the cap, returned empty content, and my harness
> scored that as the model failing to follow the format — **29% malformed, entirely manufactured
> by my own benchmark.** I nearly put that number on this slide.
>
> That's the contract risk. Not "the model returns prose". The model is fine. The *interface*
> moved four times in one afternoon, and two of those changes were silent — they didn't raise,
> they just made my numbers wrong.

Then the Django point lands on its own: your view still has to decide fail-open or fail-closed,
not because the model returns prose, but because the call can fail in ways that didn't exist
when you wrote it.

## Why this is the better slide

The original asked the audience to distrust the model. This one asks them to distrust their own
measurement — and you have the commits to prove you got caught by it. That is a much rarer talk.
