#!/bin/sh
# Run every check for the course data, the app and the Anki export.
#
# No framework - plain node and python3. Run this after any change to
# app/js/, tools/build_course.py or tools/build_words_index.py.
set -e
cd tools/..

echo "== data validation =="
python3 tools/validate.py

echo
echo "== derivation parser =="
# Family membership requires an explicit etymological derivation. This pins the
# rule that stopped nuk (the negator) being filed under not (the noun
# "swim, swimming") and the Ottoman loan bori under the inherited bri.
python3 tools/test_derivations.py

echo
echo "== prerequisite ordering =="
# A word's lexical stem must unlock no later than the word itself, the way a
# kanji's component precedes the kanji. Residual violations are allowed only
# for mutual borrowings (dalengadale <-> ngadale) that no order can satisfy.
python3 tools/test_prereq.py

echo
echo "== family completeness =="
# The family rule is strict, so it can also UNDER-link: a real derivative left
# alone would quietly weaken every level built on it. This asserts that no
# derivable edge is dropped, with a negative control.
python3 tools/test_family_completeness.py

echo
echo "== srs =="
node tools/test_srs.mjs

echo
echo "== store =="
node tools/test_store.mjs

echo
echo "== app integration =="
node tools/test_app.mjs

echo
echo "== level view =="
node tools/test_level_view.mjs

echo
echo "== pos display (level view dedup) =="
# The level files keep pos index-aligned with glosses, so the word row must
# show the first n DISTINCT labels. Added after the live E2E caught "e"
# rendering as "conjunction, conjunction". Includes a negative control.
node tools/test_pos_display.mjs

echo
echo
echo "== study card example =="
# The study card showed only the English half of an example, so "to love
# someone." appeared under the gloss for "te" with no Albanian sentence to
# show how the word is used. This extracts the REAL viewStudy() source and
# runs it against the REAL words.json, because a hand-copied view passed
# while the feature was broken. Includes a negative control.
node tools/test_study_example.mjs

echo
echo
echo "== flat index example parity =="
# course.js and build_words_index.py each pick the example for a card, and
# they had already drifted once: the lesson view applied the same-POS rule
# while the index still scanned every sense, so the review card kept showing
# the bug the lesson view had fixed. This pins them together on real data.
node tools/test_example_parity.mjs

echo
echo "== example policy =="
# The learner's rules: an example must use the word, be paired with a gloss it
# really illustrates, never cross parts of speech, and a borrowed sibling-sense
# sentence must say which sense it came from. Includes a negative control that
# reproduces the original conjunction/preposition bug.
node tools/test_example_policy.mjs

echo
echo "== example coverage =="
# Ranking must improve a sentence, never delete one. A first attempt hard-
# rejected non-matching examples and silently cost 149 cards their only
# example; this pins the floor so that cannot recur unnoticed.
python3 tools/test_example_coverage.py

echo
echo "== example pairing =="
# An example must illustrate the gloss above it. firstExample() used to take the
# first example across ALL senses, so 'e' showed the conjunction "and" beside a
# preposition sentence containing no "and". Includes a negative control.
node tools/test_example_pairing.mjs

echo
echo "== components render =="
# The build stores components as [{word, role}]; the views must turn that into
# "from e- + sille" on both the level row and the study card. Checks the app
# source, the stylesheet, and the real card data together.
node tools/test_components_render.mjs

echo
echo "== flat-index POS regression =="
# Proves the validator's POS-duplication check can actually fail. A check that
# never fails would report green forever.
python3 tools/test_pos_check.py

echo
echo "== anki export =="
# Rebuilds the .apkg, then reads it back the way Anki does: unzip, open the
# collection database, count decks and notes, and check the card templates
# only reference fields that actually exist.
if python3 -c "import genanki" 2>/dev/null; then
  python3 tools/export_anki.py
  python3 tools/verify_anki.py
else
  echo "  skipped: genanki not installed (pip3 install genanki)"
fi

echo
echo "ALL SUITES PASSED"

echo
echo "Note: tools/e2e_live.py is not run here - it needs network access and"
echo "a browser. Run it directly to check the deployed site end to end."
