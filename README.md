# albcourse

-----------------THIS IS EXPLORATORY AND NOT FINAL OR A FINISHED PRODUCT----------------------------

A spaced-repetition Albanian course built the way a kanji course is built: around
**roots and word families** rather than around characters.

You already know how Albanian is pronounced and how it is written. What is
missing is the *morphology* - the fact that so many words are one root wearing
different clothes. This course teaches them together: the root, then everything
built on it, then the descendants.

## What is here

| | |
|---|---|
| Words | 3,731 |
| Levels | 1,045 |
| Word families | 3,082 |
| Families with more than one member | 381 |
| Words containing ë / ç | 1,535 |

Levels are ordered by corpus frequency, so level 1 is genuinely the first thing
you should learn.

A level is a **session of whole word families**, not a frequency slice:

* A family is never split apart by the level boundaries. A root and its
  derivations unlock together, so a level teaches a word group rather than an
  arbitrary slice of the frequency list.
* A level holds at most 3 roots and at most 9 words, which is the
  ~9-items-per-level rhythm of a real course.
* Roots unlock in frequency order: a family starts when its own root is common
  enough to be worth teaching, not when one of its rare derivatives surfaces.
* 4 families are larger than a single session. The biggest is `për`, a
  productive prefix with 56 attested derivatives, which spans 7 levels
  (`1/7`..`7/7`). The others are `pa` (16), `bashkë` (12) and `me` (11), each
  split in two. A continuation always gets a level to itself, so a part label
  is never misleading.

Levels are titled after the root they teach, the way a Wanikani level is named
after the radical it unlocks.

### How a word joins a family

Family membership requires **an explicit derivation in the etymology text**,
never a spelling resemblance or a Wiktionary link alone. The rule is that the
first sentence states a composition, which in Wiktionary's convention always
puts a `+` between base and affix:

    From marr + -ës.              marr (take) + -em.        From gjithë + çka.
    From atë (“father”) + dhe (“land”).

The base is the last content token to the left of that `+`, after stripping
reconstruction stars, parentheticals and quoted glosses. Requiring the `+` is
what separates a derivation from a mere mention.

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
      index.json        1,045 level descriptors, loaded first
      words.json        flat card index, what a review session plays from
      levels/*.json     per-level full detail, fetched on demand
      course.json       whole-course manifest
    tools/              build and test scripts (python3 + node, no deps)
    run_tests.sh        runs all of it

The end-to-end check drives a real browser. It runs against the deployed site
by default, or a local one so a change can be verified before it is pushed:

    python3 tools/e2e_live.py --url http://127.0.0.1:8000/app/

## Rebuilding the data

The 65 MB of raw upstream downloads is not committed. Fetch it with:

    python3 tools/fetch_sources.py
    python3 tools/build_course.py
    python3 tools/build_words_index.py

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

That writes dist/albanian-roots-families.apkg (1,045 decks, 3,731 notes). It is
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
