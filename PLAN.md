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

## Ordering defect found 2026-10-01: function words were taught last

The deck taught its most common words at the very end. A family inherits a
prerequisite edge from the stem of ANY of its members, and a function word is
also a PREFIX in rarer compounds -- `esëll` (stem `sillë`, rank 30157) sat in
family `e`, so `e` could not unlock until `sillë` was ready. Those edges chain
into mutual knots (`një` <- `për` <- `gjithë` <- `kush` <- `sos` <- `ai`) that
the topological sort resolves by scheduling the rare tail first.

Fixed without discarding any edge: a word that supplies only a PREFIX to a
compound is re-homed to the family of the stem it is built on, and a family
whose own root is used only as a prefix across many unrelated stems (a
"prefix bucket", e.g. `për` held 64 members over 42 stems) has its bare prefix
detached. Every compound still follows the stem that explains it.

| word | gloss | rank | before | after |
|---|---|---|---|---|
| e | and | 2 | L652 | L1 |
| në | if | 3 | L738 | L1 |
| me | with | 14 | L747 | L8 |
| jo | not | 19 | L276 | L11 |
| nga | from/to | 25 | L750 | L15 |
| për | for | 13 | L739 | L276 |
| gjithë | all | 62 | L753 | L255 |
| ka | from/out | 20 | L749 | L279 |
| ai | he | 35 | L573 | L614 -> L19 (see below) |
| kush | who | 80 | L574 | L615 -> L35 (see below) |

This reshuffles the whole deck: 755 levels become 768, so every level number in
this document that cited the old count has been re-measured.

**Not fully solved.** Two knots survive the fix and are now *worse*:
`ai` (L573 -> L614) and `kush` (L574 -> L615) are still held back by `sos`
(rank 19473). The count of top-100 words taught after L100 fell 26 -> 11, but
the worst of them moved L215 -> L253.

### The `ai`/`kush` knot was NOT a suffix bucket (corrected 2026-10-01)

The note above blamed `sos` for being used only as a SUFFIX across unrelated
stems. That diagnosis was wrong. `sos` has no members and no dependents; it
was never a bucket. The real cause is in `components_of()`:

    kush: "...Proto-Indo-European *kʷos + *sos, meaning 'who (is) this'"
    ai:   "...Pre-Proto-Albanian *au̯- (\"away\") + *hýh ~ íh, ... Proto-Indo-European *sos (\"that\")"

Here the "+" joins two RECONSTRUCTED PIE forms, and the real `sos` appears ~40
characters later in a different clause. `_side_word()` scans forward from the
"+" for the first deck word it can match, so it matched the spelling `sos`
against the deck word `sos` ("indeed", rank 19473) and invented an edge. The
same shape hit `ti`, `këtu`, `kurrë`, `mbi`, `tetë`, `mbledh`, `rrafsh` and
`mbarë`: 20 of the deck's 283 stem edges come from Proto-* prose.

Fixed in `_stem_side()`: the stem side is cut at the first clause boundary,
and a side carrying a reconstruction marker (`*`) yields no stem. Prose is not
a composition, and a reconstructed ancestor is not a word the learner meets.

| word | gloss | rank | before | after |
|---|---|---|---|---|
| ai | he | 35 | L614 | L19 |
| kush | who | 80 | L615 | L35 |
| mbi | on/upon | 241 | L256 | L89 |
| kurrë | fist | 129 | L26 | L25 |

Top-100 words taught after L100: 11 -> 7. Worst top-100 word: L615 -> L279.
4,087 cards, zero added or dropped; 768 levels become 767. Every genuine stem
still precedes its derivative (`shkruaj` L563 vs `kruaj` L562, `esëll` = `e- +
sillë`, `bashkëpunim` = `bashkëpunoj + -im`). The rule is pinned by
`tools/test_derivations.py`, including a negative control that fails without it.

Every number below comes from `tools/measure_learnability.py`.

### 1. Early examples lean on vocabulary the learner has not met

This is the owner's own stated criterion -- short sentences that reuse
vocabulary from this lesson or an earlier one -- and the deck does not meet it.

Measured after the 2026-10-01 ordering fix. Before the fix these read
33.8% / 14.5% / 11.8% / 13.3% / 9.1% -- L1-20 got WORSE, not better:
45.3% now. That band is measured before the function words its examples need
are taught, and the fix moved those words out of L489-L753 and into L1-L15.

| Band | deck tokens in examples taught later |
|---|---|
| L1-20 | 45.3% |
| L21-100 | 9.9% |
| L101-300 | 5.4% |
| L301-500 | 1.4% |
| L501-768 | 0.5% |

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

### 4. Grammar-leaking glosses: 5 remain, triaged 2026-10-01

Re-measured over the shipped deck, scanning the headline AND every sense
gloss. **Five** cards leak, not seven:

| card | ships as | verdict |
|---|---|---|
| qetë | second-person plural simple perfect indicative of jam | sense-selection bug |
| moj | vocative particle used in a call to a woman | NOT a defect |
| dashura | feminine plural of dashur | needs a human gloss |
| vendore | locative case | sense-selection bug |
| zgjedhim | conjugation | no gloss exists |

**moj is honest.** "vocative particle used in a call to a woman" says what
the word does. Corpus: `Moj zonjë` = "My lady".

**These are upstream data, not build output.** Every one of the five glosses
is verbatim Wiktionary; the build simply failed to rewrite them. This corrects
an earlier claim here: they were never generated by the build, so no fix may
invent a replacement -- that would break the rule that nothing is written by
hand.

**qetë and vendore are the same bug: a grammar sense outranks a content
sense.**

- `qetë` also means "quiet" (corpus: `Por sot jemi të qetë` = "But today we
  are quiet"), yet its card is built from the grammatical sense.
- `vendore` has an adj entry whose senses are all `form-of`
  (`feminine singular of vendor` would render "to sell, singular") and a noun
  entry whose only content sense is `locative case`. `sense_is_content()` keys
  off the `form-of` tag, which the noun sense lacks, so grammar wins by default
  and the card carries no meaning at all.

**zgjedhim cannot be fixed without inventing a gloss.** Its upstream gloss is
the bare category name `conjugation`; there is no English definition anywhere
in the source. Corpus shows `si te zgjedhim?` = "how to choose?", so the word
is teachable -- but nothing in the build records that.

**dashura is a routing trap.** Upstream tags it `verb` while the gloss is a
nominal slot (`feminine plural of dashur`), so `friendly_verb` returns None.
Routing it to the noun path was tried and reverted: its lemma `dashur` is
itself only `participle of dua`, so the card read "participle of dua, plural" --
one grammar label swapped for another. The corpus shows the real meaning is
adjectival (`rrugët tona të dashura` = "our beloved roads"), which no source
in the build records. This needs a human gloss, not another heuristic.

**A sixth card was fixed here and was not in the leak count:** `qenë` shipped
as "they (have done) are (from jam, to be)". English has no "(have done)
are"; the perfect note was being attached to the copula. Dropping it for `to
be` yields "they are (from jam, to be)".

### 5. The tail is thinner than the head

Example coverage falls to 84.4% in L501-768 against 100% in L1-20, and
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
