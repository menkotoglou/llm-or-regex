# Data

Content warning: these are toxicity datasets. Many rows are offensive by design, and so are some
of the per-item error listings in `results/errors/`.

| file | what it is | source and licence |
|---|---|---|
| `samples/balanced-2k.csv` | 1,000 toxic / 1,000 clean news comments, for accuracy | [Civil Comments](https://huggingface.co/datasets/google/civil_comments), CC0 1.0 |
| `samples/natural-2k.csv` | 2,000 comments at natural prevalence (7.9% toxic), for cost and precision | Civil Comments, CC0 1.0 |
| `samples/train-4k.csv` | 2,000 / 2,000, disjoint from both samples above; training data for `own:train-4k` | Civil Comments, CC0 1.0 |
| `samples/manifest.json` | seed (`20261012`), threshold, pool size and prevalence of the draw | generated here |
| `handlabeled/surge-1k.csv` | 1,000 social-media comments from 2022 with human toxicity labels (501 toxic, 499 clean), held out from alt-profanity-check's training data | [Surge AI toxicity](https://github.com/surge-ai/toxicity), MIT, © 2021 Surge AI, see `handlabeled/LICENSE-surge-ai-toxicity.txt` |
| `handlabeled/obfuscation.csv` | every word-list match in the toxic items of `balanced-2k`, rewritten five ways (l33t, spaced, homoglyph, asterisk, concatenated) | derived from Civil Comments by `scripts/make_obfuscation.py` |
| `handlabeled/identity.csv` | 115 friendly sentences that mention an identity (23 identities × 5 templates), all labelled clean | written for this repo, `scripts/make_identity.py` |
| `handlabeled/extraction.csv` | 200 restaurant booking requests with gold fields, some stated plainly, some "sideways", some absent | generated from templates by `scripts/make_extraction.py` |
| `handlabeled/ood.csv` | placeholder for an out-of-distribution set you label yourself; empty, not used in any result | — |
| `wordlists/en.txt` | the banned-word list behind the `regex` arm | [LDNOOBW](https://github.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words), CC BY 4.0, © Shutterstock, see `wordlists/README.md` |

Gold labels: Civil Comments items count as toxic when `toxicity >= 0.5` (the fraction of crowd
raters who called them toxic). Surge AI labels are the dataset's own `is_toxic`.

Not used on purpose: the Jigsaw Toxic Comment (Wikipedia) set. alt-profanity-check was trained on
it, so testing there would leak in its favour. The LLMs have very likely seen Civil Comments and the
Surge AI set during pretraining; that asymmetry favours them and is stated in the talk.

`make samples` rebuilds `samples/` from the Hugging Face copy of Civil Comments (network needed);
the raw download goes to `data/raw/`, which is not committed.

If you use Civil Comments, cite: Borkan, Dixon, Sorensen, Thain and Vasserman, *Nuanced Metrics for
Measuring Unintended Bias with Real Data for Text Classification* (2019), arXiv:1903.04561.

House rule for anything you add yourself: hostility and profanity only. No example that targets a
group (sexuality, gender identity, ethnicity, religion, disability), names a real person or a
politician, or uses a slur.
