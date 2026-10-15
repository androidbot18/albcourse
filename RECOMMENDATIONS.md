# Review and recommendations

A review of `albcourse` as of `main @ 4470c1f`, covering three things: does the
roots-and-families idea come through, does the course progress sensibly, and is
it a good way to learn. Every number below was measured on the shipped data
(`data/words.json`, `data/index.json`, `data/levels/`) or the app source, not
estimated.

---

## TL;DR

The idea is good, and the pipeline is careful (strict derivation parsing,
negative-control tests, reproducible builds). Three problems hold it back:

1. **The app does not follow the course.** The Review tab hands out new cards
   in raw frequency order across the whole deck. Your first session teaches
   `të` (level 192), `më` (L192) and `që` (L193) next to level-1 words. The level
   structure the pipeline works so hard on never reaches the learner's queue.
2. **"Roots" is mostly not happening, and can only partly happen.** 2,493
   of 3,013 families (83%) have a single member. No suffix was ever shown: in
   514 cards the stem was labelled as a *prefix* (`mundësi` rendered as "from
   mund-"). About eight affixes are frequent, predictable and regular enough
   to teach as patterns; the rest are too rare, unpredictable, or collide
   with inflection. See section 2.
3. **Progression is built for the algorithm, not the learner.** The rule that a
   family is never split puts `domosdoshmëri` (rank 38,595) in **level 2**.
   Meanwhile *two* lands in L207, *bread* in L390, and *yes* (`po`) is not in the
   deck at all. 105 of the first 264 cards are conjugated forms (`jam` alone
   takes up levels 3–5).

The fixes come in four phases (bottom of this file). Phase 0 is a few days of
bug fixing that will noticeably improve the experience.

---

## 1. Bugs to fix first (P0)

These are defects in the current app. Fix them before any redesign.

| # | Problem | Where | Effect on learner |
|---|---|---|---|
| 1.1 | **New cards ignore level order.** `startStudy()` iterates `state.words`, which is `words.json` in **frequency-rank** order, not level order. | `app/js/app.js:197-202` | The first session mixes L1, L2, L192, L193, L289 words. Levels are just a browsing view. |
| 1.2 | **Failed cards never come back in the session.** `review()` sets "Again" to due in 10 min, but nothing re-inserts the card into `state.queue`. The "N still to come today" counter counts duplicates that are never added. | `app/js/app.js:218, 309-319` | A forgotten word disappears until the next time the user opens Review. Same-session relearning, the most important SRS step, is missing. |
| 1.3 | **The new-card limit is per click, not per day.** Each press of Review gives another 20 new cards. The toast says "The rest wait for tomorrow", which is false. | `app/js/app.js:199-208` | Learners overload themselves and then face a review pile-up. |
| 1.4 | **Off-by-one due dates.** `due = startOfDay(now) + interval*DAY + DAY`, so a "1 day" card is due in **2** days and every interval is a day longer than the button says. | `app/js/srs.js:92` | Intervals are longer than shown; early retention suffers. |
| 1.5 | **Direction toggle is half-wired.** It is not persisted, does not re-render, ignores `isReverseFriendly()` (never called), and both directions share one SRS item. | `app/js/app.js:430-431`, `course.js:93` | Reverse mode shows 160-character glosses as prompts, and reverse reviews corrupt the forward schedule. |
| 1.6 | **The test suite is red.** `test_pos_balance.py` fails (`unë` on L11). Because of `set -e`, the determinism test and Anki checks never run. The script's own comment admits this. | `run_tests.sh` | "All green" is not currently achievable, so regressions go unnoticed. |
| 1.7 | **Stale metadata.** README says 4,087 words / 767 levels; the data has 4,086 / 771. Level titles have wrong "+N" counts (L1 `babi, zemër, në, re +2` has 4 words; L6 lists 6 words "+4" and has 6). README also says "level 1 is genuinely the first thing you should learn", which is no longer true. | `data/index.json`, `README.md` | Erodes trust; the level map looks broken. |


**Status (P0 pass):** 1.1 to 1.5 and 1.7 are fixed in code; 1.6 is partly fixed.
- 1.1 `startStudy()` now orders new cards by level, then rank.
- 1.2 "Again" cards are re-queued at the end of the session.
- 1.3 the 20-new-cards cap is per calendar day (`stats.newToday`, persisted).
- 1.4 `due = startOfDay + interval*DAY` (a 1-day card is due tomorrow).
- 1.5 direction is persisted and restarts the queue; reverse mode skips cards that fail `isReverseFriendly()` and has its own SRS items (`<id>~r`). Existing progress is unaffected.
- 1.6 `run_tests.sh` no longer aborts on the first failure; it runs every suite and lists the failed ones. The data failures themselves remain, because they need a rebuild from the Kaikki dump, which was not reachable from this environment: `test_pos_balance` (`unë` on L11), `test_opening_policy` (rare-tail strays; it was hidden by the old abort) and `test_determinism` (needs `data/raw/`). The proper fix for the first two is the hand-curated opening in section 3.
- 1.7 level titles now name three roots and count only the hidden ones (`tools/build_course.py` and the shipped JSON patched to match); README figures and the "level 1" claim corrected.

---

## 2. The roots concept: useful, but smaller than it looks

The pitch is a kanji-style course where roots unlock word families. The first
version of this section proposed teaching about 20 affixes as WaniKani-style
"radicals". Measured against the deck, that holds for some affixes and not for
others, and the kanji analogy breaks down in one important way: a radical is
visually unambiguous, while an Albanian suffix is a string that often doubles
as an inflectional ending.

### 2.1 Which affixes are worth teaching

An affix earns a lesson only if it passes the four standard tests for teaching
an affix (Bauer & Nation's affix levels): **frequent** in this deck,
**predictable** in meaning, **regular** in form, and **not confusable** with
inflection (or the confusion is taught out loud). Counts below are
derivations the etymology parser confirms, not spelling matches.

| Affix | Meaning | Confirmed derivations | Clear (reviewed) | Verdict |
|---|---|---|---|---|
| `-im` | the act of (noun) | 78 | 75 | Teach, with the warning that `-im` is also "we" (`flasim`) |
| `-je` | the act of (noun) | 41 | 35 | Teach; `anije` (ship) is not one |
| `-(ë)si` | -ness, -ity | 24 | 20 | Teach; not the word `si` (how) |
| `-shëm` | -ful, -able | 22 | 16 | Teach, with `-shme` and `-ueshëm` |
| `-tar` | person / of | 20 | 19 | Teach, with `-ëtar` and `-tare` |
| `pa-` | un-, without | 15 | 10 | Teach; also the preposition "without" |
| `-isht` | -ly | 11 | 11 | Teach; it also names languages |
| `-ues` | one who does it | 4 | 4 | Teach (small but perfectly regular) |
| `zh-` | undo | 5 | 2 | Show in breakdowns, do not teach |
| `mos-`, `ri-`, `mbi-`, `nën-`, `kundër-`, `para-`, `bashkë-` | | 1–4 each | | Too rare in this deck |
| `për-`, `sh-`, `ç-` | | | | Not predictable: `përdor` "use" is `për-` + `dorë` "hand"; 220 words start with `sh-` and almost none are built with it |
| `-oj` | | | | A verb class, not a meaning: `shkoj`, `besoj` are not derived |
| `-ës` | | | | Collides with the case ending (`jetës`, `kohës`) |

Even the good ones drift: `rëndë` "heavy" → `rëndësi` "importance",
`sjell` "bring" → `sjellshëm` "polite". Their breakdown is a memory aid for the
answer, not something the learner can work out in advance.

Recommendations:

- Teach the eight affixes above as **patterns**, introduced inductively: on
  the level where the learner meets the **third** clear example, show a note
  that names what they have been seeing ("`mësues`, `lexues`… notice the
  pattern?"), with its spelling variants and its trap.
- Mark every breakdown as **transparent** (the parts predict the meaning;
  hand-reviewed) or **historical** (true, but not guessable). The default for
  an unreviewed word is historical.
- Keep the expectation honest. Breakdowns connect 191 words clearly and
  another 577 only historically, out of 4,086. They will not absorb most of the 2,493 one-word
  families, so 2.5 matters at least as much as this section.

### 2.2 Fix the component data

- 514 cards had their stem tagged as a **prefix**: `mundësi` →
  `[{mund, prefix}]` rendered as "from mund-". The parser read every
  equation as "affix + base", but a suffix equation (`mund + -ësi`) has the
  base on the left. It should read **`mund` + `-ësi`**.
- No card had a `suffix` role at all; the parser threw the suffix away.
- Breakdowns must come from the etymology only, never from spelling
  (`shkollë` is not `sh-` + `kollë` "cough").
- Render components colour-coded (root in one colour, affix in another)
  with each part's meaning under it, **only for transparent breakdowns**. A
  historical breakdown is shown muted and without glosses, because its stem
  gloss is often the wrong homograph (`pije` is `pi` "to drink", but the deck's
  `pi` card says "from").

### 2.3 Separate homographs, and bridge meaning drift

- `do` is glossed "some" (its primary use is the future marker / "wants").
  The family hangs `domosdo`-type words off a gloss that does not explain them.
- When a family's meaning drifts, show the bridging root sense. Under the
  headline "can, to be able to", `mundje` (defeat) and `mundim` (strain) look
  unrelated. Under "`mund`: toil, effort → *can* / *defeat* / *strain*" the
  family makes sense.
- Examples picked for the wrong homograph: `turi` "muzzle" → *Turi zgjat rreth 6
  orë* = "**The tour** lasts…"; `jon` "ion" → *Ne e bëmë atë Jon!* (a name);
  `lej` "give birth" → *Leu dielli* = "the sun rose".
- The same problem reaches breakdowns through stem glosses: `duk` "virtue"
  under `dukshëm` (visible), `ndjej` "forgive" under `ndjeshëm` (sensitive).

Use Wiktionary's numbered etymologies (`Etymology 1/2`) as separate family
keys, and require an example's English side to contain one of the gloss words
for the chosen sense.

### 2.4 Add the "guess from the parts" exercise, for transparent words only

This is the payoff of the method. Once a learner knows `mund`, show
`mundësi` *before teaching it*, with each part's meaning (`mund` *can* +
`-ësi` *-ness*), and ask what it means. Restrict it to transparent
breakdowns whose base the learner has already started: offering it on
`përdor` or `sjellshëm` would teach learners that the method does not work.

### 2.5 Give opaque words a different hook

78% of cards (3,193) have no components, no cognate and no etymology. Accept
that, and give them:

- a **mnemonic field** (start with curated ones for the top 300, and let users
  write their own);
- **contrast sets** for confusable function words (already in `PLAN.md`
  §3 and still not done);
- **loanword hooks**: many opaque words are Italian/Turkish/Greek/Latin loans
  (`makinë`, `teknologji`, `doktor`, `kapiten`). A "you already know this"
  badge is a cheap win, and the 125-card cognate limit comes from the
  extractor, not from the language.

**Status (section 2 pass):** 2.1, 2.2 and 2.4 are implemented; 2.3 and 2.5
are not.
- `components_of()` reads suffix equations the right way round: the base gets
  role `base`, the suffix role `suffix`. No lone-prefix breakdown of a suffix
  derivation remains (459 before). `base` deliberately creates no
  prerequisite edge, so the level order is unchanged; promoting bases to
  edges is a scheduling change that belongs with 3.1 and needs a full
  rebuild to evaluate.
- `tools/affixes.py` holds the eight taught patterns (meaning, variants,
  trap) and the hand-reviewed list of 191 transparent words, with the
  reasons for the exclusions. It annotates the levels during the build, and
  can re-derive the shipped data in place when the Kaikki dump is not
  available (`python3 tools/affixes.py`).
- Patterns land on the level of their third clear example: `-(ë)si` L14,
  `-je` L60, `-shëm` L65, `-im` L68, `pa-` L78, `-tar` L142, `-isht` L287,
  `-ues` L290. The level map marks those levels.
- The app colour-codes breakdowns, glosses each part on transparent cards,
  mutes historical ones, and shows "New word. Guess it from the parts" on the
  first review of a transparent word whose base has been started.
- `tools/test_affixes.py` and the rewritten `tools/test_components_render.mjs`
  (which now runs the real `componentsLine()` and `isGuessCard()`) pin all of
  this, with negative controls.

---

## 3. Course progression

### 3.1 Replace "a family is never split" with "root first, tail later"

The family-unsplittable rule causes most of the strange ordering:

- **L2** teaches `do` (rank 4) along with `domosdoshëm` (20,233),
  `domosdoshmërisht` (22,083), `medoemos` (22,302), `doemos` (30,516) and
  `domosdoshmëri` (38,595).
- **L9** teaches `njëmbëdhjetë` *eleven* (rank 10,616), but *two* is L207, *three*
  L216, *ten* L232.
- 21 words ranked below 8,000 appear in L1–30, and **286 of 771 levels** span
  more than 10,000 frequency ranks.

Proposed rule:

1. A derivative unlocks only after its root **and** its affix are known
   (keep the prerequisite edges).
2. A derivative is scheduled in its **own frequency band** (e.g. no more than
   ~2,000 ranks ahead of the current frontier). Rare derivatives wait.
3. When a derivative unlocks, its lesson shows the **whole known family tree**
   with the new word highlighted. The family is reunited visually, not by
   forcing everything into one session.

This keeps what is good about grouping (the root is always taught first, and
the connection is always shown) without front-loading rare vocabulary.

### 3.2 Hand-curate the opening (~first 300 words)

A frequency list from OpenSubtitles makes a poor syllabus for the first weeks.
Today:

- `po` (*yes*) is **missing** from the deck, and `e` (rank 2: *and* plus the
  linking article) was removed rather than fixed.
- Function words held out of the opening are not spread through the course:
  they all land together around **L192–L210** (`të`, `më`, `që`, `jo`, `ka`,
  `kjo`, `këtë`, `shumë`, `por`, `edhe`, `gjithë`, `pak`, `dy`, `pa`, `pas`,
  `ose`…). That is 38 top-200 words after L100, packed into a wall.
- Greetings come late (`mirëdita` L56, `përshëndetje` L81), and so does basic
  food (`bukë` L390).
- `unë` (*I*) fails the existing test and sits at L11.

Recommendation: a small hand-written `opening.yaml` that sets the first ~25
levels by theme (greetings and yes/no; pronouns plus `jam`/`kam`; numbers 1–10;
family; food and drink; time and days; question words; the 10 core verbs).
After that, the algorithm takes over. Spread the deferred function words one or
two per level from L20 onwards instead of in one block.

The README's rule that "nothing is written by hand" is the main thing
preventing this. Drop it. A small, reviewed **overrides layer** (glosses,
opening order, example picks) on top of the generated data is normal for any
serious course.

### 3.3 Take inflected forms out of the vocabulary deck

371 cards (9%) are inflected forms, and they are concentrated at the start: 105
of the first 264 cards. `jam` alone takes 3 levels (22 cards). The glosses also
go wrong: `ishin` = "they (used to) **was**", `qenë` = "they are" (it is the
participle *been*), `jem`/`jesh` glossed as indicative when they are
subjunctive.

- Replace per-form cards with **one paradigm card per verb** (present
  table), plus pattern lessons ("verbs in `-oj`: `punoj → punon, punojmë…`").
- Keep at most the 2–3 highest-frequency forms as standalone recognition cards.
- The opening policy says grammar is "taught in a separate course", yet the
  deck is full of grammar. Either link that course, or add a **minimal
  grammar spine**. Learners cannot read the examples without it: definite
  endings (`-i/-u/-a/-t`), the linking article (`i/e/të/së`), the `të`
  subjunctive, `do të` future, and `nuk`/`mos`.

### 3.4 Make level size consistent

Level sizes run from 1 to 9 words (81 levels have 1–2 words; median 6).
Separate **levels** (content groups) from **sessions** (what you do today): a
lesson should present a steady 8–12 items (words + affixes), pulling the next
level forward when the current one is tiny.

### 3.5 Gate levels by mastery

Nothing is locked. Unlock level N+1 when roughly 80–90% of level N has reached
"familiar" (interval ≥ 3 days). This is the WaniKani/Bunpro loop, and it is
what makes levelling up feel like an achievement.

---

## 4. Content quality

Correctness matters more than coverage. A wrong translation actively teaches
the wrong thing.

### 4.1 Wrong or misleading headline glosses (examples)

| card | ships as | should be |
|---|---|---|
| `në` (L1) | if | **in**, at (the "if" sense is secondary) |
| `do` (L2) | some | future marker / wants (from `dua`) |
| `botë` | Earth | **world** |
| `qenë` | they are | been (participle of `jam`) |
| `ishin` | they (used to) was | they were |
| `errësirë`, `hua` | raw Wiktionary head-line (`errësirë f (plural…`) | darkness; loan |

40% of glosses (1,629) are comma lists of several senses. Headline **one**
sense; put the rest behind a "more meanings" toggle.

### 4.2 Example sentences

Example coverage is high (93%), but quality is uneven because many come from
subtitle alignments:

- Mistranslations: `babi` → *Babi po vjen* = "It's good." (should be *Dad is
  coming*); `mami` → *Jam Demeti, mami* = "She's Ali's fiancée."; `do` → *Nuk do
  bije!* = "No it's not."; `jem` → *Të jem Beyoncé* = "It is being Beyoncé."
- Wrong orthography: 13 examples write `eshte/nje/per` without `ë`, and 11
  contain Lithuanian `ė` (`Do jesh mirė`). An Albanian course should never
  show misspelt Albanian.
- Early examples rely on unknown words: 38% of deck tokens in L1–20 examples
  are taught later. `PLAN.md`'s own target is below 15%.

Recommendations:

- Run an **orthography gate**: reject sentences containing characters outside
  the Albanian alphabet, and frequent `ë`-less misspellings.
- Run a **translation-agreement gate**: the English side must contain a word
  from the selected sense's gloss (or a synonym). This would have caught
  `turi`, `jon`, `lej`, `babi` and `mami`.
- For L1–50, **write the example sentences** (i+1: only known words plus the
  target). About 300 short sentences, reviewed by a native speaker, will do
  more for retention than another heuristic.
- Add a **"Report a problem"** button on every card (it can just open a
  prefilled GitHub issue), so learners help clean the data.

### 4.3 Get a native-speaker pass on the top 1,000

`PLAN.md` already sends four cards to a native speaker. Extend that to every
headline gloss and example in the first ~150 levels. It is the highest-leverage
quality step available.

### 4.4 Use more than one frequency source

OpenSubtitles skews towards dialogue, drama vocabulary and misspellings (no
`ë`). Average its rank with a general web/news list (e.g. the Leipzig
Corpora or HPLT counts the project already uses for examples), so `kapiten` and
`doktor` do not outrank everyday words.

---

## 5. Learning experience and engagement

The app has three views: a level grid, a static word list, and flashcards.
These additions would make it a course rather than a deck.

### 5.1 A proper lesson flow (Learn → Quiz → Review)

Opening a level now just lists words; there is no "learn these" action.
Suggested flow:

1. **Family tree intro.** The root in the centre, known relatives greyed out,
   new words highlighted, affixes colour-coded with their meanings.
2. **Word cards.** One by one: word, breakdown, gloss, one short example,
   mnemonic.
3. **Immediate quiz.** Each new item once in each direction (multiple choice
   first, then typed). Only items that pass go into SRS.
4. **"You can now read…"**: one or two sentences made only of known words.

### 5.2 More exercise types

Flip-and-self-grade is the weakest form of recall. Add:

- **Typed answers** for production (EN→SQ), with tolerant `ë`/`ç` matching
  ("close, mind the ë") and an on-screen ë/ç key.
- **Cloze** from the example sentence (`Ai ___ mban syze.` → `nuk`).
- **Build the word**: drag root + affix tiles to form the target.
- **Guess from the parts** (see §2.4).
- **Contrast drills** for confusable sets (`nuk/mos/jo`, `dhe/edhe`, `se/që`,
  `ose/apo`, `këtu/atje`).

### 5.3 Motivation and feedback

The data for most of this is already stored (`stats.days`, item intervals):

- **Streak** and a **daily goal** (reviews or new words), shown in the top bar.
- **Level map status colours**: locked / in progress / done / mastered.
- **Text coverage meter**: "You know the words behind 62% of everyday
  Albanian text." It is computed from frequency ranks you already have, and it
  is the most motivating number a vocabulary course can show.
- **Level-up moment** when a level unlocks, with a summary of the families
  learned.
- **Review forecast** (due today / tomorrow / this week) on the Progress tab.
- **Leech handling**: after 6–8 lapses, flag the card and offer to add a
  mnemonic.

### 5.4 Usability

- Keyboard shortcuts: Space to reveal, 1–4 to grade, plus an Undo-last-grade
  button.
- Persist the direction choice, and give each direction its own SRS item
  (`id:sq2en`, `id:en2sq`). Introduce reverse cards only once the forward card
  is "familiar".
- Configurable new-cards-per-day and a session cap (e.g. 10/20/30).
- Make it installable as a PWA with offline caching (it is already static), so
  phone users can study on the go.

### 5.5 Scheduler

The SM-2 variant is fine to start with, but consider **FSRS** (open source,
available in JS): it gives fewer reviews for the same retention. If you keep
SM-2, fix 1.2–1.4 and add an interval fuzz (±5%) so cards learned together do
not all fall due on the same day.

---

## 6. Engineering and process

- **Get the suite green, then keep it green.** Either fix `unë` or update the
  test, and move the slow determinism test behind a flag rather than relying
  on test order.
- **Prune `tools/`.** There are 70+ scripts, many of them one-off probes
  (`probe_violation.py`, `find_pathish.py`, `measure_form_gap.py`,
  `serve_check_cognate.py`, …). Move experiments to `tools/scratch/` or delete
  them, and keep `build`, `validate`, `measure`, `export` and `test_*`.
- **Compute the example once.** `course.js` and `build_words_index.py` both
  choose the example, and a parity test exists only because they drifted. Do
  it in the build, ship the result, and delete the client-side logic and the
  parity test.
- **Turn `PLAN.md` into a plan.** It reads as a debugging log. Move history to
  `CHANGELOG.md`, and keep `PLAN.md` to goals, current metrics and the next
  three tasks.
- **Measure learner outcomes, not just pipeline correctness.** Most tests guard
  extraction regressions. Add a small set of learner-facing quality gates that
  fail the build:
  - top-200 words all present and all taught by L60
  - no rank > 5,000 word before L30
  - L1–20 untaught-token share < 15%
  - zero examples with non-Albanian characters
  - zero headline glosses containing grammar labels
- **Root-cause shared bugs once.** The `ROOT` path bug appeared twice
  (#21, 2026-10-02 in `PLAN.md`). Use one `paths.py` module that every script
  imports.

---

## 7. Suggested roadmap

**Phase 0: fix what is broken (days)**
- [ ] Queue new cards in level order, not rank order (1.1)
- [ ] Re-queue "Again" cards in the same session (1.2)
- [ ] Daily new-card limit (1.3)
- [ ] Off-by-one due date (1.4)
- [ ] Direction: persist it, use `isReverseFriendly`, separate SRS items (1.5)
- [ ] Green test suite; fix README counts and level-title "+N" (1.6, 1.7)
- [ ] Orthography gate on examples; fix the glosses in §4.1

**Phase 1: progression (1–2 weeks)**
- [ ] Hand-curated opening (~25 levels) via an overrides file; add `po`, restore `e`
- [ ] "Root first, tail later" scheduling instead of unsplittable families
- [ ] Spread deferred function words across levels instead of L192–210
- [ ] Collapse inflected-form cards into paradigm cards; minimal grammar spine
- [ ] Fix homograph example mismatches; add bridging root senses (`do`, `mund`)
- [ ] Mastery gating between levels

**Phase 2: roots made visible (2–3 weeks)**
- [x] Suffix extraction; fix stem/prefix role labels (2.2)
- [x] Eight affix patterns, introduced at their third clear example (2.1)
- [x] Colour-coded breakdown, transparent vs historical (2.2)
- [x] "Guess from the parts" on transparent words (2.4)
- [ ] Family-tree view
- [ ] Learn → Quiz → Review lesson flow
- [ ] "Build the word" exercise (transparent words only)

**Phase 3: engagement and polish (ongoing)**
- [ ] Typed answers, cloze, contrast drills
- [ ] Streaks, daily goal, text-coverage meter, level-up screen, forecast
- [ ] Native-speaker pass over the first 150 levels; hand-written i+1
      examples for L1–50
- [ ] Report-a-problem button; mnemonics; PWA/offline; consider FSRS

---

## What to keep

Plenty here is worth preserving:

- the strict, test-pinned derivation rule (no spelling-resemblance families);
- prerequisite ordering (stem before derivative);
- negative controls on tests, and the reproducible build;
- a static, dependency-free, privacy-first app;
- the Anki export that preserves the level/family structure;
- the habit of measuring before claiming (`measure_learnability.py`).

Most of the recommendations above change *what the pipeline optimises for*
(learner experience over data purity), not how carefully it is built.
