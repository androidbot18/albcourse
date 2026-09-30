# Course plan

Goal: make the course teachable, not merely correct. Pre-RC, so renumbering is
free. Measure before/after on every change, and only claim what a command
printed.

**Out of scope, by owner decision: audio.** No pronunciation, recordings,
TTS or listening exercises. The course is text-only by design.

## Baseline (main @ 63543a6)

- 4,087 cards / 755 levels / 3,011 families (495 multi-member)
- stem-after-word violations: 0
- example coverage: 3,751 (91.8%); 84.0% in L501-755 vs 100% in L1-20
- cognate hooks: 125 cards, rendered on the revealed side
- verb families present-first; multi-member families in their own session;
  noun share of L1-10 is 0.30

Reproduce with `python3 tools/measure_learnability.py` and
`python3 tools/measure_coverage.py`.

## Shipped (PRs #1-#14)

1. Verb families teach present tense first (`jam` L2 is 9/9 present).
2. Multi-member families get their own session (226 single-family, 37
   continued, 492 mixed).
3. Cognate hooks on 125 cards.
4. Pictureable nouns in the opening levels (noun share 0.30).

## Open work, highest leverage first

Every number below comes from `tools/measure_learnability.py`.

### 1. Early examples lean on vocabulary the learner has not met

This is the owner's own stated criterion -- short sentences that reuse
vocabulary from this lesson or an earlier one -- and the deck does not meet it.

| Band | deck tokens in examples taught later |
|---|---|
| L1-20 | 33.8% |
| L21-100 | 14.5% |
| L101-300 | 11.8% |
| L301-500 | 13.3% |
| L501-755 | 9.1% |

L1-20 is by far the worst and it is the band that matters most: 145 tokens
taught later plus 71 not in the deck at all. Concrete cases:

- L1 `nuk` -> `Ai nuk mban syze.` (`syze` is L334)
- L1 `të` -> `të duash ndokënd.` (`duash` is L16)
- L5 `se` -> `Më duket se ke nevojë për disa shokë të rinj.`
  (`disa` L751, `për` L739, `nevojë` L55, `duket` L32, `më` L490)

Fix: rescore examples by how much of the sentence is already known, and prefer
an example restricted to the current band. A sentence the learner cannot parse
is worse than no sentence -- it teaches that Albanian is unreadable.

### 2. 77.8% of cards have no hook at all

3,179 cards (168 of them in the first 30 levels) have no components, no
cognate and no etymology. The first 30 are mostly function words -- `të nuk
është dhe se unë mund ju si duhet ne kjo kam këtë shumë por jam je` -- which
cannot be derived, so they need a different treatment rather than a hook.
Minimum: contrast sets, since these are exactly the words learners confuse.

### 3. Confusable sets are scattered across the whole course

- negation: `nuk ne jo` land far apart in level order
- conjunction: `dhe se por që ngase ose apo ndërsa kurse` likewise
- 1,528 cards (37.4%) open with a multi-sense comma gloss, which is where
  confusion concentrates

Fix: a minimal-pair drill that presents a set together, so the contrast is the
lesson rather than an accident of frequency order.

### 4. 133 glosses still leak grammar terminology

The form-gloss rewrite (#12/#13) fixed 348, but these remain:
`këtë -> accusative masculine/feminine singular of ky and kjo`,
`vdekur -> participle of vdes`,
`thotë -> he/she/it (subjunctive) say`.
A beginner reads "accusative masculine singular of" as the answer, not as a
description. These are the same class as the 348 already fixed.

### 5. The tail is thinner than the head

Example coverage falls to 84.0% in L501-755 against 100% in L1-20, and
component coverage falls to 15.5% from 26.3%. If a learner stops early the
course is in better shape, which should be an explicit and defensible property
rather than an accident.

## Explicitly NOT problems

- **Thin levels.** 85 levels hold 1-2 words; 7 are family continuations and 78
  are unsplit small families (`bukur`/`bukuri`) that cannot fill a session.
  Measured, then cleared. Do not "fix" these.
- **Root-homogeneous levels as a goal.** Measured: 60% root-homogeneous means
  3,033 sessions that are 83% single words, and the filler variant produced
  `në nëse nëpër ndopak ndriçim ndriçoj të dhe se`. A kanji-style component
  system is not achievable in Albanian; prerequisites made visible is the honest
  ceiling.
- **Cognate coverage above 125 cards.** Only 156 cards carry a source
  language. The earlier 1,320 figure was an 8x overclaim.

## Definition of done for the next pass

- L1-20 examples: untaught deck tokens under 15%
- Every grammar-leaking gloss either rewritten or documented as intentional
- Negation and conjunction sets each taught as one contrast session
- A test that fails if any of the three reverts
