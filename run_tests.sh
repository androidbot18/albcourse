#!/bin/sh
# Run every check for the course data and the app.
#
# No dependencies, no framework - plain node and python3. Run this after any
# change to app/js/ or tools/build_course.py.
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
echo "ALL SUITES PASSED"
