#!/bin/sh
# Run every check for the course data, the app and the Anki export.
#
# No framework - plain node and python3. Run this after any change to
# app/js/, tools/build_course.py or tools/build_words_index.py.
# Deliberately no `set -e`: a red suite must not hide the suites after it (the
# old script aborted on the first failure, so the determinism and Anki checks
# silently never ran). Every suite runs; failures are collected and the script
# exits non-zero at the end.
cd "$(dirname "$0")"
FAILED=""
step() {
  "$@" || FAILED="$FAILED\n  $*"
}

echo "== data validation =="
step python3 tools/validate.py

echo
echo "== derivation parser =="
# Family membership requires an explicit etymological derivation. This pins the
# rule that stopped nuk (the negator) being filed under not (the noun
# "swim, swimming") and the Ottoman loan bori under the inherited bri.
step python3 tools/test_derivations.py

echo
echo "== prerequisite ordering =="
# A word's lexical stem must unlock no later than the word itself, the way a
# kanji's component precedes the kanji. Residual violations are allowed only
# for mutual borrowings (dalengadale <-> ngadale) that no order can satisfy.
step python3 tools/test_prereq.py

echo
echo "== early level balance =="
# Levels 1-10 were 9% noun and 55% verb: a learner's first contact with the
# language was almost entirely function words. These pin the pictureable-noun
# rebalance, including the two ways it was got wrong first (union-POS, and
# prepending instead of interleaving).
step python3 tools/test_pos_balance.py

echo
echo "== opening policy =="
# Levels 1-10 opened with `të` (rank 1, conjunction) and `në` (rank 3,
# conjunction) because the frequency list is OpenSubtitles and only one of
# its top 45 tokens is a content noun. Grammar is taught in a separate
# course, so closed-class words are held out of the opening by a named set;
# conjugations stay. This also pins the two silent failures that produced a
# green build and a wrong deck: the POS namespace mismatch and the frequency
# budget that admitted exactly the words it was meant to exclude.
step python3 tools/test_opening_policy.py

echo
echo "== root first, tail later =="
# A family's rare members used to follow the root in the next level, so do
# (rank 4) taught doemos (rank 30516) in level 2 and pushed une past level
# 10. The tail now comes back at its own frequency; this pins that, with a
# negative control, and checks the opening holds no rare-tail word.
step python3 tools/test_tail_later.py

echo
echo "== shipped levels match the scheduler =="
# Re-runs assign_levels() on the shipped cards (no raw sources needed) and
# fails if any level file would change. Catches a scheduler change committed
# without the data it produces. Restores data/ afterwards.
step python3 tools/relevel.py --check

echo
echo "== cognate hooks =="
# The source-language form shown on a card ("from Latin soca"). The failure
# mode this guards is subtle: the extractor can return the English gloss
# instead of the source word, which looks plausible and teaches nothing.
step python3 tools/test_cognates.py

echo
echo "== family completeness =="
# The family rule is strict, so it can also UNDER-link: a real derivative left
# alone would quietly weaken every level built on it. This asserts that no
# derivable edge is dropped, with a negative control.
step python3 tools/test_family_completeness.py

echo
echo "== srs =="
step node tools/test_srs.mjs

echo
echo "== store =="
step node tools/test_store.mjs

echo
echo "== app integration =="
step node tools/test_app.mjs

echo
echo "== level view =="
step node tools/test_level_view.mjs

echo
echo "== pos display (level view dedup) =="
# The level files keep pos index-aligned with glosses, so the word row must
# show the first n DISTINCT labels. Added after the live E2E caught "e"
# rendering as "conjunction, conjunction". Includes a negative control.
step node tools/test_pos_display.mjs

echo
echo
echo "== study card example =="
# The study card showed only the English half of an example, so "to love
# someone." appeared under the gloss for "te" with no Albanian sentence to
# show how the word is used. This extracts the REAL viewStudy() source and
# runs it against the REAL words.json, because a hand-copied view passed
# while the feature was broken. Includes a negative control.
step node tools/test_study_example.mjs

echo
echo
echo "== flat index example parity =="
# course.js and build_words_index.py each pick the example for a card, and
# they had already drifted once: the lesson view applied the same-POS rule
# while the index still scanned every sense, so the review card kept showing
# the bug the lesson view had fixed. This pins them together on real data.
step node tools/test_example_parity.mjs

echo
echo "== example policy =="
# The learner's rules: an example must use the word, be paired with a gloss it
# really illustrates, never cross parts of speech, and a borrowed sibling-sense
# sentence must say which sense it came from. Includes a negative control that
# reproduces the original conjunction/preposition bug.
step node tools/test_example_policy.mjs

echo
echo "== example coverage =="
# Ranking must improve a sentence, never delete one. A first attempt hard-
# rejected non-matching examples and silently cost 149 cards their only
# example; this pins the floor so that cannot recur unnoticed.
step python3 tools/test_example_coverage.py

echo "== shipped example gates =="
# The live site served 'dhe' -> 'CTE dhe STEM.' while every local suite
# passed. HPLT is a wiki corpus, so abbreviations and product codes survive
# every language gate, and a sense guard cannot catch it because the English
# side genuinely says 'and'. These assert the SENTENCE, not the sense.
step python3 tools/test_shipped_examples.py

echo "== learner-facing form glosses =="
# Form cards used to read as dictionary grammar ('third-person singular present
# indicative of jam'). These assert the rewrite is grammatical against real
# Wiktionary slot strings, that it refuses rather than guesses, and that no
# shipped card is left half-converted.
step python3 tools/test_form_gloss.py

echo "== form gloss: person agreement and inferred lemmas =="
# Two defects the merged rewrite still shipped: 'they (has done) are' is false
# English, and nine main entries whose only gloss is form-of phrasing were
# never converted. Also pins the two cards that must KEEP the raw gloss.
step python3 tools/test_form_gloss_person.py

echo "== reviewed headline glosses =="
# Section 4.1: në headlined "if", botë "Earth", qenë "they are". These are
# fixed by a small reviewed overrides layer (tools/gloss_overrides.py); this
# pins each fix in the shipped deck and bans raw Wiktionary head lines.
step python3 tools/test_gloss_overrides.py

echo "== orthography gate on examples =="
# Section 4.2: examples written without ë ("eshte", "nje"), with Lithuanian
# ė, or in historical spelling. tools/orthography.py rejects them at build
# time; this pins the gate and checks every example the deck can show.
step python3 tools/test_orthography.py

echo "== example selection guard =="
# Two components disagreed on what counts as "this card has an example", so
# words were skipped and shipped bare: 'mire' (adjective 'good') because its
# ADVERB sense had one, and 'e' because the article sense 'a whole' carries an
# English 'and'. Both are asserted here against real corpus lines.
step python3 tools/corpus/test_select_guard.py

echo
echo "== deployed e check (negative control) =="
# verify_live_merge.py shipped two VACUOUS checks for the 'e' card: both
# passed on the exact sentence they were written to reject, so the article
# sense went live under the gloss "and". This asserts they ARE vacuous,
# and that the replacements actually reject the defect.
step python3 tools/test_verify_live.py

echo
echo "== example pairing =="
# An example must illustrate the gloss above it. firstExample() used to take the
# first example across ALL senses, so 'e' showed the conjunction "and" beside a
# preposition sentence containing no "and". Includes a negative control.
step node tools/test_example_pairing.mjs

echo
echo "== components render =="
# The build stores components as [{word, role}] plus a transparent/historical
# flag; the real componentsLine() must render "built from mund + -ësi" or
# "historically from për- + dorë" on the level row and the study card, and
# isGuessCard() must only fire on a new transparent card with a known base.
step node tools/test_components_render.mjs

echo
echo "== affix patterns and breakdowns =="
# A breakdown is only worth showing if it is true. Pins: breakdowns come from
# the etymology, never spelling (shkollë is not sh- + kollë); only reviewed
# words are offered as guess-from-the-parts; a historical breakdown never
# shows a wrong-homograph stem gloss; -im the noun is not -im "we"; patterns
# land on their third clear example; shipped data matches tools/affixes.py.
step python3 tools/test_affixes.py

echo
echo "== flat-index POS regression =="
# Proves the validator's POS-duplication check can actually fail. A check that
# never fails would report green forever.
step python3 tools/test_pos_check.py

echo
echo "== anki export =="
# Rebuilds the .apkg, then reads it back the way Anki does: unzip, open the
# collection database, count decks and notes, and check the card templates
# only reference fields that actually exist.
if python3 -c "import genanki" 2>/dev/null; then
  step python3 tools/export_anki.py
  step python3 tools/verify_anki.py
else
  echo "  skipped: genanki not installed (pip3 install genanki)"
fi

echo
echo "== reproducible build =="
# The deck was not reproducible: 460 of 4086 words moved between
# levels 143 and 257 depending on PYTHONHASHSEED, because the family
# re-homing pass both read a family minimum rank and removed members
# from it in one loop. This rebuilds under several hash seeds and
# compares a digest of every level file. Slow by nature; pass --fast
# for just the two seeds that disagreed.
step python3 tools/test_determinism.py

# This one is LAST because it rebuilds the deck seven times and is slow.
echo
if [ -n "$FAILED" ]; then
  printf "FAILED SUITES:$FAILED\n"
  exit 1
fi
echo "ALL SUITES PASSED"

echo
echo "Note: tools/e2e_live.py is not run here - it needs network access and"
echo "a browser. Run it directly to check the deployed site end to end."
