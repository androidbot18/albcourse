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
