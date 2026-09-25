# RUNBOOK — πώς τρέχεις τα πειράματα

Οδηγός βήμα προς βήμα για το `llm-or-regex.zip`. Ο κώδικας και τα αρχεία είναι αγγλικά· αυτός ο οδηγός είναι για σένα.

**Συνολικός χρόνος:** ~25′ δικός σου + ~2 ώρες που τρέχει μόνο του.
**Κόστος:** μόνο το βήμα 5 ξοδεύει χρήματα (~6,700 κλήσεις ανά μοντέλο, ~1M input tokens).

---

## 0. Προϋποθέσεις

- **Python 3.11+** (το `scikit-learn==1.9.0` δεν εγκαθίσταται σε παλαιότερο). Έλεγχος: `python3 --version`
- `make`, `curl`, `git`
- API keys για όποιον provider θα μετρήσεις
- ~2 GB ελεύθερο δίσκο (το Civil Comments κατεβαίνει από το HuggingFace)

```sh
unzip llm-or-regex.zip && cd llm-or-regex
git init && git add -A && git commit -m "harness"   # ο commit hash μπαίνει στα slides
```

---

## 1. Setup (2′)

```sh
make setup        # venv + dependencies
make wordlist     # κατεβάζει τη λίστα LDNOOBW (403 λέξεις) για το regex arm
```

Έλεγχος: `ls data/wordlists/en.txt` και `.venv/bin/python -c "from profanity_check import predict_prob; print(predict_prob(['go to hell, you scum']))"` → κάτι κοντά στο `[0.76]`.

---

## 2. Samples (5–15′, κατεβάζει δεδομένα)

```sh
make samples
```

Φτιάχνει τρία αρχεία από το Civil Comments, seed `20261012`, και τα γράφει στο `data/samples/`:

| | τι είναι | για ποιο πείραμα |
|---|---|---|
| `balanced-2k` | 1.000 toxic / 1.000 clean | accuracy |
| `natural-2k` | 2.000 σε φυσική συχνότητα (~8% toxic) | cost, precision |
| `train-4k` | 2.000 / 2.000, **disjoint** από τα άλλα δύο | training του `own` arm |

Τυπώνει ένα manifest· κράτα το `pool_prevalence`, θα το πεις στη σκηνή.

**Αν το HuggingFace δεν παίζει** (εταιρικό δίκτυο, rate limit): κατέβασε το `train.csv` του Kaggle *Jigsaw Unintended Bias* και τρέξε
`.venv/bin/python -m bench.data --source csv --csv /path/to/train.csv`

**Το `surge-1k`** (τα σχόλια του 2022) είναι ήδη μέσα στο zip, δεν χρειάζεται τίποτα.

---

## 3. Dry run (1′, χωρίς δίκτυο και χρήματα)

```sh
make dryrun
```

Τρέχει όλα τα modules με ένα ψεύτικο LLM arm. Αν αυτό περάσει, το pipeline δουλεύει και μπορείς να αφήσεις το βήμα 5 να τρέξει με ησυχία. Καθάρισε μετά τα ψεύτικα αποτελέσματα:

```sh
rm -rf results/balanced-2k/llm_fake_any results/latency/llm_fake_any.json results/determinism/llm_fake_any.json
```

---

## 4. Τα δωρεάν πειράματα (10′)

```sh
make local          # πειράματα 1–3: regex, apc, own σε balanced-2k και natural-2k + latency + determinism sanity
make obfuscation    # πείραμα 7: l33t, spacing, homoglyphs, αστερίσκοι, concatenation
make identity ALL_ARMS="regex apc own:train-4k"    # πείραμα 9, χωρίς LLM προς το παρόν
```

**Αυτά αντικαθιστούν τα γκρι νούμερα** στα slides 9, 10, 10b, 11 και 12. Τα δικά μου μετρήθηκαν σε sandbox· τα δικά σου είναι αυτά που θα πεις.

Τι να κοιτάξεις αμέσως:

```sh
cat results/summary.md              # ο βασικός πίνακας
cat results/obfuscation.md          # ο πίνακας του slide 11
cat results/identity.md             # ο πίνακας του slide 10b
head -40 results/errors/apc_balanced-2k.md    # διάλεξε 5 λάθη για το slide 10
```

Στο `results/latency/apc.json` είναι το `cold_start` → `max_rss_mb`. Αυτό το νούμερο μπαίνει στο slide 12 και καθορίζει το instance tier στο επόμενο βήμα.

---

## 5. Τα LLM arms (τρέχει ~1–2 ώρες, ξοδεύει χρήματα)

```sh
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...

make llm \
  LLM_SMALL=llm:anthropic:<small-model-id> \
  LLM_FRONTIER=llm:anthropic:<frontier-model-id>
```

**Όγκος ανά μοντέλο:** 2.000 (balanced) + 2.000 (natural) + 250 (latency) + 600 (determinism) ≈ 4.850 κλήσεις, ~750k input tokens, ~30k output. Πολλαπλασίασε με την τιμή του provider για να ξέρεις τι θα πληρώσεις πριν πατήσεις enter.

**Για τέσσερα arms** (small + frontier σε δύο providers) τρέξε το `make llm` δεύτερη φορά με τα άλλα IDs. Τα αποτελέσματα του πρώτου δεν πειράζονται.

Χρήσιμα:
- **Είναι resumable.** Ctrl-C, rate limit, πεσμένο wifi: ξανατρέχεις την ίδια εντολή και συνεχίζει από εκεί που έμεινε. Τίποτα δεν πληρώνεται δεύτερη φορά.
- **Αργό ή 429;** `make llm ... WORKERS=4`. Γρήγορο δίκτυο και ψηλά rate limits: `WORKERS=16`.
- Η πρόοδος βγαίνει στο stderr ανά 100 items, με `errors=` και `malformed=`. Αν το `malformed` είναι πάνω από ~5%, σταμάτα και κοίτα τι επιστρέφει το μοντέλο (`results/<sample>/<arm>/run0.jsonl`, πεδίο `raw`) — μπορεί να θέλει μια λέξη παραπάνω το prompt.
- **Το latency να το τρέξεις από το μηχάνημα και το δίκτυο που θα αναφέρεις.** Όχι από cafe wifi το πρωί της ομιλίας.

Μετά, τα hand-labelled σετ από τα LLM arms (γεμίζουν τις στήλες στα slides 10b και 11):

```sh
make handlabeled LLM_SMALL=... LLM_FRONTIER=...     # ~2.000 κλήσεις ακόμα ανά μοντέλο
```

Το `ood.csv` είναι άδειο και δεν σπάει τίποτα· αν θέλεις το πείραμα 5 (contamination check), γράψε ~200 δικά σου σχόλια με labels πριν το τρέξεις.

---

## 6. Κόστος (5′ δικά σου)

Άνοιξε το `config/prices.toml` **την ημέρα που το τρέχεις** και συμπλήρωσε:

- `as_of` = η ημερομηνία, `eur_per_usd` = η ισοτιμία ΕΚΤ εκείνης της ημέρας
- ένα `[llm."<provider>:<model-id>"]` section ανά arm, με το model ID **ακριβώς** όπως το έδωσες στο `--arm` (χωρίς το `llm:` μπροστά)
- `[compute]` = το instance που θα έτρεχες πραγματικά το apc (με βάση το RSS από το βήμα 4) και η τιμή του ανά ώρα

```sh
make cost LLM_SMALL=... LLM_FRONTIER=...
```

Τυπώνει ευρώ ανά 1M ταξινομήσεις ανά arm, από τα **πραγματικά** token counts που γύρισε το API.

---

## 7. Cascade και τελικός πίνακας (2′)

```sh
make cascade LLM_SMALL=... LLM_FRONTIER=...
cat results/cascade/natural-2k_*.md
```

Σαρώνει ζεύγη `(LO, HI)` και δείχνει ανά γραμμή: τι ποσοστό της κίνησης φτάνει στο LLM, το blended P/R/F1, και το blended κόστος. **Διάλεξε τη γραμμή που θα έστελνες πραγματικά σε production** — αυτή μπαίνει στο slide 21, μαζί με τα LO/HI.

```sh
make report LLM_SMALL=... LLM_FRONTIER=...
cat results/summary.md
```

Θέλεις και τις τρεις εκδοχές της πολιτικής για malformed output, είναι slide από μόνο του:

```sh
.venv/bin/python -m bench.report --arm regex --arm apc --arm own:train-4k \
  --arm llm:anthropic:<small> --arm llm:anthropic:<frontier> --policy closed
```

---

## Σειρά, συνοπτικά

```sh
make setup wordlist samples dryrun          # μια φορά
make local obfuscation                      # δωρεάν, 10′
make identity ALL_ARMS="regex apc own:train-4k"
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=...
make llm LLM_SMALL=... LLM_FRONTIER=...     # άφησέ το να τρέξει
make handlabeled LLM_SMALL=... LLM_FRONTIER=...
# συμπλήρωσε το config/prices.toml
make cost cascade report LLM_SMALL=... LLM_FRONTIER=...
git commit -am "results"                    # ο hash μπαίνει στο slide 7 και 9
```

---

## Πού πάει τι

| αρχείο | slide |
|---|---|
| `results/summary.md` | 9 (ο βασικός πίνακας), 12 (latency, cost) |
| `results/errors/*.md` | 10 (διάλεξε 5 λάθη ανά arm) |
| `results/identity.md` | 10b |
| `results/obfuscation.md` | 11 |
| `results/latency/*.json` | 12 (p50/p95, cold start, RSS) |
| `results/determinism/*.json` | 13 (disagreement @ t=0) |
| `results/cascade/*.md` | 21 (traffic share, blended F1, blended cost) |
| `git rev-parse --short HEAD` | 7 και 9 (commit hash) |

Για να μπουν στο deck: άλλαξε τα νούμερα στο `build_deck.js` (ψάξε `[__]` και `sandbox(`) και τρέξε `node build_deck.js`.

---

## Αν κάτι σπάσει

| σύμπτωμα | τι συμβαίνει |
|---|---|
| `scikit-learn==1.9.0` δεν εγκαθίσταται | Python < 3.11. Φτιάξε venv με νεότερο. |
| `data/wordlists/en.txt missing` | δεν έτρεξε το `make wordlist`. |
| `no sample named 'balanced-2k'` | δεν έτρεξε το `make samples`, ή απέτυχε το HF download. |
| `No price for ... in config/prices.toml` | το key δεν ταιριάζει ακριβώς με το model ID που έδωσες στο `--arm`. |
| `results/latency/<arm>.json missing` | το `make cost` για τοπικά arms θέλει πρώτα `make latency` (μέσα στο `make local`). |
| πολλά `errors=` στο LLM run | rate limit. `WORKERS=4` και ξανατρέξε — συνεχίζει από εκεί που έμεινε. |
| πολλά `malformed=` | το μοντέλο απαντά πρόζα. Κοίτα το `raw` στο jsonl. **Μην το κρύψεις** — είναι νούμερο για το slide 10. |
