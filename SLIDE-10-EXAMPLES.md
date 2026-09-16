# Slide 10 — error examples, filtered under rule 6

Source: `results/errors/*_balanced-2k.md`. Five per classical arm.

Rule 6 filter applied: no example may target a group (sexuality, gender identity, ethnicity,
religion, disability), name a real person or a politician, or use a slur. Rejections are listed
under each arm so you can see what the filter cost.

The LLM arms' five each are pending the run.

---

## regex — false positives (word-list hits on innocuous text)

1. **`tied up`** — "…increase over-utilization and more rationing of urgent care for lack of
   providers **tied up** with non-essential preventative care."  *Healthcare policy.*
2. **`Viagra`** — "Neither **Viagra**, penicillin, nor Lithium exist in water already… have so
   permeated our water…"  *Pharmacology.*
3. **`suck`** — "In other words, the Leafs **suck**! Right? (Read the article not the headline —
   the columnists don't write the headlines)"  *Hockey.*
4. **`Suck`** — "UA needs to keep the sports that are relevant to Alaskans: skiing, hockey, and
   basketball…"  *University sports funding.*
5. **`butt`** — "He had best get his **butt** to California where they can hail him a hero
   otherwise I doubt his chances anywhere else look too rosy."

All five scored 1.000. The list is 403 words; these are the cost of the last one.

**Rejected:** 10 of the 23 false positives hit on `sex` / `sexual` / `sexuality` / `sexually`
in abuse-survivor, canon-law, Planned-Parenthood and consent-trial contexts; `rape` on a comment
about prosecuting rapists; `boobs` and `panties` on comments naming real people. One genuine loss:
**`hooker`** matching a rugby comment about a player who "could not tackle" — the single best
illustration in the file, rejected only because it names the player. Redact the name and it's usable.

## apc — the question mismatch

False positives (profanity-shaped, not hostile):

1. **0.868** — "shame on you."
2. **0.736** — "That is silly."
3. **0.597** — "What about Canada Geese that poop in parks — should we ask the Police to shoot them too?"

False negatives (hostile, no profanity):

4. **0.007** — "Execute him."
5. **0.003** — "The shortest stories get the stupidest comments."

Put 1 and 4 side by side: **"shame on you." flagged at 0.868, "Execute him." missed at 0.007.**
That is the whole slide. apc answers "is there profanity?"; the product asks "is this toxic?"

**Rejected:** the highest-scoring false positive (0.911) targets immigrants and religion;
0.674 is a racial slur; Louis CK, Trudeau, the Bundys, Pelosi and "Barry" all name real people or
politicians. Among false negatives, most of the lowest scores are about Trump, Putin, Kim,
Muslims or "Moslem invaders" — all out.

## own:train-4k — what task-matched labels buy, and what they cost

False positives (it learned that political heat means toxic):

1. **0.862** — "That is silly."  ← *also an apc false positive at 0.736. One three-word sentence
   defeats both classical arms. Use this.*
2. **0.877** — "Its funny that the Cup final means anything. Theres an embarrassment on here
   alright but its smiling and waving in its ignorance."
3. **0.857** — "Sometimes management and coaching can't see the trees for the forest. I cringed,
   once again…"

False negatives:

4. **0.081** — "If you cant afford to do business without a government handout your business plan
   **sucks**."  ← *caught by the 403-word regex, missed by the trained model. The inverse pair.*
5. **0.121** — "Silly, Grade 9 level writing, as usual."

**Rejected:** 14 of the top 18 false positives are about Trump, Obama, the POTUS, the Democratic
Party, Christian principles or white supremacists — this arm's errors are overwhelmingly political
speech, which is itself the finding, but none of it can go on the slide. Among false negatives:
"sleazy greaseball" (ethnic slur), "Mark Weber should have been EUTHANIZED" (names a person),
a comment attributing behaviour to fetal alcohol syndrome (disability), and Murkowski/Sullivan.

---

## Two pairs worth building the slide around

- **"shame on you."** → apc 0.868, flagged. **"Execute him."** → apc 0.007, missed.
- **"That is silly."** → flagged by apc *and* own. **"…your business plan sucks."** → caught by
  the regex, missed by own.
