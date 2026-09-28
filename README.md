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
| Levels | 184 |
| Word families | 3,278 |
| Families with more than one member | 245 |
| Words containing ë / ç | 1,535 |

Levels are ordered by corpus frequency, so level 1 is genuinely the first thing
you should learn. Within a level, related words sit together.

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
      index.json        184 level descriptors, loaded first
      words.json        flat card index, what a review session plays from
      levels/*.json     per-level full detail, fetched on demand
      course.json       whole-course manifest
    tools/              build and test scripts (python3 + node, no deps)
    run_tests.sh        runs all of it

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

That writes dist/albanian-roots-families.apkg (184 decks, 3731 notes). It is
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
