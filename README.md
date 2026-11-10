# albcourse

-----------------THIS IS EXPLORATORY AND NOT FINAL OR A FINISHED PRODUCT----------------------------

A spaced-repetition Albanian course built the way a kanji course is built: around
**roots and word families** rather than around characters.

You already know how Albanian is pronounced and how it is written. What is
missing is the *morphology* - the fact that so many words are one root wearing
different clothes. This course teaches them together: the root, then everything
built on it, then the descendants.

**The course now opens with the Conversation Core** (`CONVERSATION_PLAN.md`,
steps 1-3): 1,000 dictionary words and 157 phrases in 52 units ordered by
situation, before the roots-and-families course begins. Steps 4-6 of that
plan (native-speaker review export, typed and gap-fill exercises) are still
to do.

**Scope: text only.** No audio, no pronunciation drills, no recordings. That
is a deliberate decision, not an oversight - see `PLAN.md`.

## What is here

| | |
|---|---|
| Cards | 4,072 (3,915 words, 157 phrases) |
| Levels | 658: the 168-level Conversation Core, 116 more main-course levels, then 374 optional extended levels |
| Word families | 3,373 |
| Families with more than one member | 408 |
| Words containing ë / ç | 1,689 |
| Cards with an example sentence | 3,569 (87.6%) |
| Words with a cognate hook | 125 |

(These figures were stale for several PRs -- the deck had already been
rebuilt twice. They now come from `data/words.json`; check with
`python3 tools/measure_learnability.py`.)

Levels 1-168 are the **Conversation Core**: 52 units of about twenty items,
ordered by situation (hello and goodbye, introductions, numbers and money,
the café, shopping, directions, time, family, home, health, weather, the
phone, opinions), not by word family or subtitle frequency. It is
hand-written in `tools/core/*.txt` and read by `tools/conversation_core.py`,
and the build refuses to run unless:

* every word has an example of 8 words or fewer in which every other word
  was already taught (a form counts once its word is known);
* every unit ends with a dialogue made only of taught items;
* every headline gloss is 30 characters or fewer;
* no card is an inflected form of another card. A verb shows its key forms
  on its own card (`shkoj` · `shkon`, `shkova`, `shkuar`), a noun its
  definite and plural. Only `do` and `ka` remain as form cards in the deck.

Eleven short grammar notes appear on the level that first needs them.
`python3 tools/measure_conversation.py` prints where the 214-word everyday
checklist (`tools/conversation_checklist.py`) is taught: 210 are in the
core, 160 of them within the first month at 20 new items a day, and 4 are
deliberately left out. The core takes 58 days at that pace. All of it was
written without a native speaker and is waiting for one (`PLAN.md`,
"Native-speaker review queue").

The deck is built from Wiktionary, which has no entry at all for some core
words: `pra` (*so*), `ndonjë` (*any*), `sikur`, `vërtet`, `sigurisht`,
`problem`, `mirupafshim` (*goodbye*)... 41 of them are added by hand in
`tools/added_words.py`, each with a reviewed gloss, example and forms. The
build refuses an entry that would shadow a real Wiktionary card.

After the core, levels are ordered by when a word family's root becomes
common enough to teach, with grammar words held back and some pictureable
nouns pulled forward. That part is an approximation, not a hand-built
curriculum. The Review tab follows level order, then the order each level
teaches its items in, and new cards are capped at 20 per day.

The **main course** is levels 1-284: 1,789 cards, the core plus everything
ranked up to 5,000 in the frequency list and the stems those words are
built on. It covers 83.9% of the tokens in the frequency list, counting an
inflected form of a taught word as known, and 60.9% by exact form
(`python3 tools/measure_coverage.py`). The other 2,283 words, rank above
5,000, form an optional **extended track** (levels 285-658, marked
`extended`) that adds about 2 points more. The app introduces them only
after the learner turns the track on from the level map. See
RECOMMENDATIONS.md section 3.6.

A level is a **session of whole word families**, not a frequency slice:

* A family is taught together: a root and its everyday derivations unlock
  in the same session, so a level teaches a word group rather than an
  arbitrary slice of the frequency list.
* Root first, tail later: a family's rare members (rank above 1,200) do not
  ride the root into an early session. They come back as their own level,
  "do (rarer words)", once the course reaches their frequency. Before this,
  `do` (rank 4) taught `doemos` (rank 30,516) in level 2 and pushed `unë`
  ("I") out of the first ten levels; 20 families now resume this way.
* A level holds at most 9 words, which is the ~9-items-per-level rhythm of
  a real course. A family with more members than fit gets its own
  sessions; a level that mixes families is the normal case after the core (461 of 490),
  because forcing one family per level was measured and produced 3,033
  sessions that were 83% single words.
* Roots unlock in frequency order: a family starts when its own root is common
  enough to be worth teaching, not when one of its rare derivatives surfaces.
* 13 families have more than 9 words. The biggest are `për` (23 words),
  `jam` (22), `kam` (14), and `dua`, `shkoj`, `vras` and `a` (13 each). A
  continuation always gets a level to itself, so a part label is never
  misleading.

Levels are titled after the root they teach, the way a Wanikani level is named
after the radical it unlocks.

### Word parts and affix patterns

The same `+` equations give each card its breakdown: `pa- + fund`,
`mund + -ësi`. A breakdown is **transparent** when the parts predict the
meaning (hand-reviewed; 191 words) and **historical** otherwise (`përdor` is
`për-` + `dorë` "hand"; 577 words). Transparent ones are colour-coded with a
meaning under each part, and the first review of one, once its base is known,
asks you to guess the word from its parts.

Eight affixes are taught as patterns (`-im`, `-je`, `-(ë)si`, `-shëm`,
`-tar`, `pa-`, `-isht`, `-ues`), each on the level where you meet its third
clear example. Most of the vocabulary is opaque roots and loans, so this is a
layer on top of the deck, not its backbone. See `tools/affixes.py` and
RECOMMENDATIONS.md section 2.

### How a word joins a family

Family membership requires **an explicit derivation in the etymology text**,
never a spelling resemblance or a Wiktionary link alone. A derivation is a
sentence that puts a `+` between base and affix:

    From marr + -ës.              marr (take) + -em.        From gjithë + çka.
    From atë (“father”) + dhe (“land”).

The base is the last content token to the left of that `+`, after stripping
reconstruction stars, parentheticals and quoted glosses. Requiring the `+` is
what separates a derivation from a mere mention.

Every sentence is scanned, not just the first: `esëll` names its base only in
the third — *“Interpretible as e- + sille”* — and a first-sentence rule split it
from its root `e`. A **comparison** is not a derivation, though. `nuk` carries
the aside *“typologically compare Latin nōn (‘not’) … (< ne + ūnus ~ ūnum)”*,
which describes Latin, not Albanian, so that sentence is skipped and `nuk`
stays its own root. So is a `+` that sits entirely inside parentheses.

This is stricter than it sounds, and deliberately so. Wiktionary's structured
fields cannot be trusted as a derivation graph:

* `parents` is extracted from the etymology text, so it picks up **English**
  gloss words. `nuk` has parents `["one", "not"]`, where that `not` is the
  English word inside *compare Latin nōn ("not")*. The old build linked on it,
  so the negator *not, don't* sat in the same family as the noun *swim,
  swimming*.
* `derived` is a **co-occurrence** list, not a derivation graph. `bri` ("rib")
  lists `bori`, an Ottoman loan meaning *bugle*; `zbres` ("descend") lists
  `falas`, `falem`, `fale`, `falje`, `faltore`.

Cognates and homographs are excluded for the same reason: `tmerr` ("terror") is
*a cognate* of `marr`, not a derivative, and `marre` ("shame") and `marrtë`
("twilight") are homographs of `marr` with unrelated meanings. `tools/
test_derivations.py` pins all of these cases, in both directions.

## Running it

The app is plain HTML, CSS and ES modules. No build step, no dependencies.

    ./run_tests.sh            # every check, ~3 seconds
    python3 -m http.server 8000
    # then open http://localhost:8000/app/

It must be served over http, not opened as a file:// URL - the course data is
fetched, and browsers block that on file://.

## How progress is stored

Entirely in localStorage, on the device. There is no account, no server, no
telemetry. The Progress tab can export a JSON backup and re-import it, which is
the only way to move progress between devices.

Clearing site data or using a private window loses progress, so export if you
care about it.

## Layout

    app/                 the study app (this is what GitHub Pages serves)
      index.html
      css/style.css
      js/srs.js         scheduler - SM-2 variant, no DOM, unit tested
      js/store.js       persistence - versioned, defensive against bad data
      js/course.js      data loading and card helpers
      js/app.js         the views and event wiring
    data/               generated course data
      index.json        658 level descriptors, loaded first
      words.json        flat card index, what a review session plays from
      levels/*.json     per-level full detail, fetched on demand
      course.json       whole-course manifest
    tools/              build and test scripts (python3 + node, no deps)
    run_tests.sh        runs all of it

The end-to-end check drives a real browser. It runs against the deployed site
by default, or a local one so a change can be verified before it is pushed:

    python3 tools/e2e_live.py --url http://127.0.0.1:8000/app/

## Rebuilding the data

The two sources are committed as pinned snapshots in `data/sources/`
(the Kaikki Albanian dump of 2026-10-15, zipped, and the frequency list),
so a build needs no network and always gives the same deck:

    python3 tools/fetch_sources.py      # unpack and verify into data/raw/
    python3 tools/build_course.py
    python3 tools/build_words_index.py

CI (`.github/workflows/rebuild-data.yml`) rebuilds from the snapshots and
fails if the committed `data/` differs. To move to a newer Kaikki dump, run
`python3 tools/fetch_sources.py --refresh`, update the hashes it prints,
rebuild, review the data diff, and commit the snapshot and data together.

build_course.py decides which sense of a word becomes its headline gloss, which
is the part worth reading before changing anything there.

## Anki export

The whole course also ships as an Anki deck. The structure is preserved
rather than flattened, because the structure is the point: **one deck per
level, named for the root that level teaches**, and every note carries its
root, family, family size, level and frequency rank as separate fields you can
search and sort on.

    pip3 install -r tools/requirements.txt
    python3 tools/export_anki.py

That writes dist/albanian-roots-families.apkg (658 decks, 4,072 notes; the extended track's decks are named
"Albanian extended L..."). It is
gitignored because it is a build artifact; regenerate it any time.

Import it in Anki with File > Import, and pick the single .apkg file. Notes
carry a deterministic guid, so re-importing after a data rebuild updates the
existing notes in place instead of duplicating them.

To check an export without opening Anki:

    python3 tools/verify_anki.py

It unzips the package, opens the collection database, and counts decks, notes
and level tags, then confirms the card templates only reference fields that
actually exist. The test runner also runs a negative control, which corrupts
the deck ids and asserts the verifier fails - a check that cannot fail is not
a check.

## The scheduler

A light SM-2 variant. Four grades (Again / Hard / Good / Easy), an ease factor
per card, and an explicit learning ladder so a forgotten word returns the same
day instead of drifting weeks out. Intervals are shown on the buttons before you
commit, so the cost of each answer is never a surprise.

## Sources

- Definitions, parts of speech, etymology, example sentences: English
  Wiktionary, extracted by Kaikki.org
- Frequency ordering: hermitdave/FrequencyWords, OpenSubtitles 2018 build

Glosses are editorial judgements made automatically; some are wrong. If a word
looks mis-glossed, check the Wiktionary entry and open an issue.
