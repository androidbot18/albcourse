#!/usr/bin/env python3
"""Verify the exported .apkg the way Anki reads it.

genanki writing the file without error proves only that genanki is happy with
itself. Anki parses the SQLite schema, reads the collection, and renders the
templates - so open the package as a zip, query the collection database
directly, and confirm the card templates actually reference real fields.
"""
import json
import os
import re
import sqlite3
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APKG = os.path.join(ROOT, "dist", "albanian-roots-families.apkg")

# Expected shape of the export, read from the course data so these
# assertions cannot drift from what the generator actually produced.
_course = json.load(open(os.path.join(ROOT, "data", "course.json"),
                      encoding="utf-8"))
EXPECT_LEVELS = _course["level_count"]
EXPECT_WORDS = _course["word_count"]

failures = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)
    return cond


def main():
    if not os.path.exists(APKG):
        print("FAIL: %s missing - run export_anki.py" % APKG)
        return 1

    # 1. It must be a zip, which is what Anki expects.
    check(zipfile.is_zipfile(APKG), "package is a valid zip archive")
    with zipfile.ZipFile(APKG) as z:
        names = z.namelist()
        check("collection.anki2" in names, "contains collection.anki2")
        check("media" in names, "contains the media map")
        db_name = "collection.anki2"
        tmp = tempfile.mkdtemp()
        z.extract(db_name, tmp)

    db = os.path.join(tmp, db_name)
    con = sqlite3.connect(db)
    cur = con.cursor()

    tables = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    check("notes" in tables and "cards" in tables,
          "database has notes and cards tables")

    notes = cur.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    cards = cur.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
    decks = cur.execute("SELECT COUNT(DISTINCT did) FROM cards").fetchone()[0]
    check(notes == EXPECT_WORDS,
          "all %d notes present (got %d)" % (EXPECT_WORDS, notes))
    check(cards == EXPECT_WORDS,
          "all %d cards present (got %d)" % (EXPECT_WORDS, cards))
    check(decks == EXPECT_LEVELS,
          "%d distinct decks, one per level (got %d)" % (EXPECT_LEVELS, decks))

    # 2. The note payload must be real genanki JSON, not garbage.
    row = cur.execute("SELECT flds, tags FROM notes LIMIT 1").fetchone()
    check(row is not None, "at least one note row")
    flds, tags = row
    fields = flds.split("\x1f")
    check(len(fields) == 12, "note has 12 fields (got %d)" % len(fields))
    check(any(f.strip() for f in fields), "fields carry text")
    check("albanian" in (tags or ""), "notes are tagged 'albanian'")

    # 3. Every level tag must be present, one per level.
    all_tags = [r[0] for r in cur.execute("SELECT tags FROM notes")]
    levels = set()
    for t in all_tags:
        for tag in (t or "").split():
            if tag.startswith("level"):
                levels.add(tag)
    check(len(levels) == EXPECT_LEVELS,
          "all %d level tags present (got %d)" % (EXPECT_LEVELS, len(levels)))
    # Anki tags are compared as exact strings, so the expected set has to
    # use the same zero-padding the exporter writes. Derive the width from
    # the level count instead of assuming 2 -- the exporter pads to the
    # level count for the same reason the filename padding does.
    tag_width = len(str(EXPECT_LEVELS))
    expected_tags = set("level%0*d" % (tag_width, i)
                        for i in range(1, EXPECT_LEVELS + 1))
    extra = levels - expected_tags
    missing = expected_tags - levels
    check(not extra, "no level tags outside the real range (extra: %s)"
          % sorted(extra)[:5])
    check(not missing, "no missing level tags (missing: %s)"
          % sorted(missing)[:5])

    # 4. Albanian diacritics must survive the SQLite round trip.
    dia = cur.execute(
        "SELECT COUNT(*) FROM notes WHERE flds LIKE '%ë%' OR flds LIKE '%ç%'"
    ).fetchone()[0]
    check(dia > 0, "notes carry ë/ç (got %d rows)" % dia)

    # 5. The card templates must only reference fields that exist.
    models = cur.execute("SELECT models FROM col").fetchone()
    check(models is not None, "collection has a models blob")
    parsed = json.loads(models[0])
    model = list(parsed.values())[0]
    flds_named = [f["name"] for f in model["flds"]]
    tpl = model["tmpls"][0]
    used = set(re.findall(r"{{[#^]?([A-Za-z]+)", tpl["qfmt"] + tpl["afmt"]))
    unknown = used - set(flds_named) - {"FrontSide", "Front", "Back"}
    check(not unknown, "templates reference only real fields (bad: %s)"
          % sorted(unknown))
    check("{{Albanian}}" in tpl["qfmt"], "question shows the Albanian word")
    check("{{English}}" in tpl["afmt"], "answer shows the English gloss")
    check("{{Root}}" in tpl["qfmt"], "question shows the root")
    check("{{FrontSide}}" in tpl["qfmt"], "question reuses the front template")

    con.close()

    print()
    if failures:
        print("APKG VERIFICATION FAILURES (%d):" % len(failures))
        for f in failures:
            print("  x %s" % f)
        return 1
    print("APKG VERIFIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
