# Plan: learn conversational Albanian vocabulary quickly and easily

Written 2026-11-10 against `main @ 379ceb16`. This plan is about one goal
only: a learner who studies 10-15 minutes a day should be able to understand
and say the words and phrases of everyday conversation within about two
months. `RECOMMENDATIONS.md` covers the course as a whole and `PLAN.md` is
the build log; where they overlap with this file, this file sets the order
of work.

## Status

Steps 1-3 are built: the core is levels 1-168 (52 units, 1,000 words, 157
phrases, 52 dialogues, 11 grammar notes), form cards are folded into their
words, and `tools/test_conversation_core.py` enforces the gates. Run
`python3 tools/measure_conversation.py` for the current figures. Of the
gates below, one is met only in part: 210 of the 214 checklist words are in
the core (4 are deliberately skipped, named in the checklist file), and 50
of them come after the first month. Step 4 is done only as far as the core's
own glosses; the review CSV, the translation gate, the report link, and all
of steps 5 and 6 are still to do. The figures under "What was measured"
describe the course before this work.

## Summary

The pipeline is careful and the first 23 hand-curated levels are good. After
them, the course stops serving a conversational learner, for five reasons:

1. **A fifth of the course is conjugated and declined forms taught as
   separate words**, concentrated exactly where a beginner is.
2. **Everyday words arrive late or never**, because the order comes from
   film subtitles and from word families, not from what people need to say.
3. **There are no phrases.** Conversation runs on fixed chunks (`si je?`,
   `më vjen keq`, `sa kushton?`), and the deck has single words only.
4. **Too many high-frequency glosses and example translations are wrong.**
5. **The app only tests recognition.** You flip a card and grade yourself;
   you never have to produce a word, and you never use it in a sentence.

The fix is a **Conversation Core**: about 1,000 dictionary words and 150
phrases, ordered by situation, each with one short correct gloss and a
sentence built only from words already taught, practised by typing and
filling gaps and not only by flipping. The existing roots-and-families course
stays, as the track that follows the core.

## What was measured

Every figure is from the shipped `data/words.json`, `data/sources/sq_50k.txt`
and `tools/measure_learnability.py`. The main course is levels 1-348, 1,665
cards.

| Finding | Figure |
|---|---|
| Main-course cards that are an inflected form (`shkon`, `jetën`, `këtyre`) | 366 of 1,665 (22%) |
| The same, in levels 24-100 | 157 of 376 (42%) |
| Form cards whose English is broken (`we (used to) was`, `arriveed`) | 34 |
| Multi-word cards (phrases) | 0 |
| Share of running text covered by the exact forms taught, after L50 (267 cards) | 56.1% |
| The same after the whole main course (1,665 cards) | 70.0% |
| What the 1,000 most frequent forms alone would cover | 77.3% |
| L1-20 example sentences: words in them not yet taught | 46.4% |
| Main-course glosses that are a comma list of senses | 833 of 1,665 |

Coverage is counted by exact form here. `README.md` reports 83% because it
counts any inflection of a taught word as known. Both are true; the exact
count shows the cost of the current order: the last 1,398 cards add 14 points.

**Everyday words.** I checked 214 common conversational words against the
deck. This is my own list, and step 1 below commits it so the check can be
repeated.

| Where the word is | Count | Examples |
|---|---|---|
| Not in the deck | 17 | `majtas`, `djathtas` (left, right), `tualet`, `stacion`, `farmaci`, `lodhur` (tired), `pëlqen`, `kushton`, `Shqipëri`, `Kosovë` |
| Only in the optional extended track | 12 | `shqip` (L370), `shqiptar`, `lek`, `faturë`, `prind`, `mot` |
| After level 120 (more than a month in, at 20 new cards a day) | 81 | `mirëmëngjes` L242, `quhem` L212, `blej` L239, `restorant` L315, `çaj` L271, `mjek` L307, `biletë` L333, `drekë` L261 |

So 110 of 214 (51%) are out of reach in the first month. Meanwhile film
vocabulary is early: `kapiten` L27, `gjak` (blood) L28, `dreqin` L45,
`vdes` (die) L55, and the `vras` (kill) family has 13 cards.

**Correctness.** I read the 170 most frequent dictionary-word cards after the
opening. I am not a native speaker, so treat these as a queue to confirm, but
about 20 glosses are wrong or misleading and about 10 example translations do
not match their Albanian:

| Card | Ships as | Conversational meaning |
|---|---|---|
| `njeri` | anyone | person |
| `a` | or | question particle (`A je mirë?`) |
| `na` | we | us |
| `pas` | at | after |
| `deri` | to | until |
| `le` | to give birth | let (`le të shkojmë`, let's go) |
| `pres` | to cut | to wait (its form `prit` is "wait!") |
| `thua` | fingernail | you say |
| `dikë` | great desire, lust | someone (object form) |
| `kujdes` | regard | care; careful! |
| `eshtë` | fiber | a misspelling of `është` from the subtitles; drop |

Example translations: `Ju jeni çmendur` = "Thank you", `Jetë vonë sot` =
"What's the rush?", `Unë të pashë` = "Ok, see you", `Jo, kam ca pune` =
"Maybe later".

**The app.** One exercise: reveal and self-grade, Albanian to English by
default. No typed answers, no gap-fill, no lesson step before a word enters
review, no sentence practice, a fixed 20 new cards a day, and no streak or
goal. Example sentences are short (median 4 words), which is right and should
be kept.

## Target

A learner on the Conversation Core, at 15-20 new items a day:

| By | Can do |
|---|---|
| Week 1 (about 120 items) | greet, thank, apologise, introduce themselves, say where they are from, count |
| Week 4 (about 500 items) | order food, shop and pay, ask the way, talk about family, time and plans |
| Week 8 (about 1,150 items) | hold a simple everyday conversation; every word on the checklist is known |

Gates the build should enforce once the work is done:

- every checklist word is in the core, none after item 1,000
- no inflected-form card in the core
- at least 150 phrase cards
- every core item has an example of 8 words or fewer in which every other
  word was taught earlier (0% untaught, against 46.4% today in L1-20)
- every core headline gloss is one sense, 30 characters or fewer, with no
  grammar label

## The work, in order

### 1. Define the Conversation Core (data, about a week)

- Add `tools/conversation_core.py`: the reviewed list of situations and the
  words each needs, in the style of `tools/opening_levels.py`. Start from the
  214-word checklist and the present opening. Add
  `tools/measure_conversation.py` to print the table above, so every later
  step is measured.
- Situations, in teaching order: hello and goodbye; please, thanks, sorry;
  introducing yourself; yes, no and the small words; numbers and money; café
  and restaurant; shopping; directions and transport; time, days and plans;
  family and people; home and daily routine; feelings and health; weather;
  phone and messages; opinions and connecting words (`sepse`, `por`,
  `ndoshta`, `mendoj se`).
- Fill each situation to about 60-70 words by taking the most frequent words
  that fit it, then top up with the most frequent general words not yet
  placed. Hand-add the 17 missing words through `tools/added_words.py`.
- Move film vocabulary (`kapiten`, `gjak`, the `vras` family) out of the core
  into the later track. Blending in a second, non-subtitle frequency list
  (RECOMMENDATIONS 4.4) does this mechanically for the rest.
- Units are about 20 items, by situation, each named for what it lets you
  do ("Order a coffee"). Word families stay visible on the card and still
  order the later track, but they no longer decide the order of the core.
  This is the one real change of direction in this plan.

### 2. One card per word, not per form (data, about a week)

- Collapse the 366 form cards into their dictionary word. That alone frees
  about seven weeks of new-card slots at 50 a week.
- A verb card shows its key forms on the answer side: `shkoj` · ti `shkon` ·
  `shkova` (went) · `kam shkuar`. A noun shows its definite and plural
  (`djalë`, `djali`, `djem`). An adjective shows its article (`i mirë`,
  `e mirë`).
- The few forms that are irregular and very common (`është`, `ishte`, `tha`,
  `erdhi`, `dha`) are taught inside phrases and example sentences, with the
  form linked back to its word, not as cards of their own.
- Keep the form table in the data so that a typed form is accepted as a
  correct answer and so coverage can go on counting forms.
- Add four short grammar notes at the point of first need, not a grammar
  course: the definite ending, the linking article, `të` + verb, `do të`
  future, `nuk` against `mos`.

### 3. Phrases and readable sentences (content, 2-3 weeks)

- Write about 150 phrase cards, ten or so per situation: `Si je?`,
  `Mirë, faleminderit`, `Më vjen keq`, `S'ka gjë`, `Në rregull`,
  `Si quhesh?`, `Quhem ...`, `Nuk kuptoj`, `Flisni anglisht?`,
  `Sa kushton?`, `Ku është ...?`, `Do të doja ...`. A phrase is taught
  whole, before its words are analysed.
- Write one example for every core word, using only earlier words plus the
  target. Roughly 1,000 short sentences. Selecting from corpora has been
  tried at length and still leaves 46% untaught words in the first 20 levels;
  for the core, writing them is cheaper than another heuristic. A test
  enforces the rule using the form table from step 2.
- End each unit with a six-line dialogue made only of taught items. It is
  the proof to the learner that the unit worked.

### 4. Correct, short glosses (content, 1-2 weeks, alongside step 3)

- Review every core headline by hand through `tools/gloss_overrides.py`,
  starting with the table above. One sense, the conversational one; other
  senses go behind "more meanings".
- Add the translation-agreement gate from RECOMMENDATIONS 4.2 for the later
  track, where sentences are still picked automatically.
- Export the core (word, gloss, example, translation) as one CSV for a
  native speaker. Everything in steps 3 and 4 is hand-written, so one review
  pass covers it. This is the most valuable single outside contribution the
  project can get.
- Add a "report a problem" link on every card that opens a prefilled issue.

### 5. Make the app teach, not just test (app, 2-3 weeks)

In order of effect on learning:

- **Lesson before review.** New items arrive five at a time: see the word
  with its sentence, pick it from four choices, then type it. Only then does
  it enter spaced repetition.
- **Exercises that get harder as a word matures.** First reviews: recognise
  (Albanian to English). Next: fill the gap in its sentence. Then: type the
  Albanian for the English, with `e` accepted for `ë` and `c` for `ç` but
  pointed out, and on-screen `ë` `ç` keys. Phrases end as "put the words in
  order". Being able to say a word is the goal, so production is the default
  end state, not an optional direction toggle.
- **Short, steady sessions.** Reviews first, then new items. Let the learner
  choose 5, 10, 15 or 20 new a day, and cut new items automatically when
  more than about 100 reviews are due. A pile-up is the usual reason people
  quit.
- **Progress in the learner's terms.** Per unit: "You can now: order a
  coffee". Overall: words you can use, share of everyday speech covered, a
  streak and a daily goal. The data is already stored.
- **Small things.** Space and 1-4 keys, undo last grade, repeated-failure
  cards flagged and shown with their family or a contrast (`nuk`/`mos`/`jo`),
  installable offline on a phone.

### 6. Keep the rest as the second track

After the core, the present main course continues as "the next 1,000 words",
in its root-and-family order, where that structure helps most: a learner who
knows `punë` and `-tar` can guess `punëtor`. The extended track is unchanged.
The Anki export gains the core as its first decks.

## Decisions for the owner

1. **Order by situation, not by family, for the first 1,000.** Everything in
   step 1 depends on it. I recommend it: the measured cost of family order in
   the core is that half of everyday vocabulary is more than a month away.
2. **Audio.** `PLAN.md` rules it out, and this plan respects that. It is
   still the largest gap for a course whose aim is conversation, since a
   learner who has only read `faleminderit` may not catch it when spoken. If
   the decision is ever reopened, recorded or generated audio for the 150
   phrases alone would be the place to start.
3. **Who reviews the Albanian.** Steps 3 and 4 produce about 1,150 glosses
   and sentences written without a native speaker. They should not be called
   finished until one has read them.

## What stays as it is

The strict derivation rule and its tests, the pinned and reproducible build,
the static no-account app with local progress, the scheduler, the 23-level
opening (it becomes the first units of the core), and the habit of measuring
before claiming.
