#!/usr/bin/env python3
"""Export the course to an Anki deck (.apkg).

The point of this course is that cards are grouped by ROOT and WORD FAMILY
rather than by characters, so the export must preserve that structure instead
of flattening everything into one list. Each level becomes its own Anki deck,
named with the root it teaches, and every card carries its family, root and
level in dedicated fields you can search, filter and sort on.

Run:  python3 tools/export_anki.py
Out:  dist/albanian-roots-families.apkg
"""
import json
import os
import re
import sys

import genanki

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "levels")
DIST = os.path.join(ROOT, "dist")

# A stable deck id. Anki stores scheduling by note id, so the deck id matters
# only for grouping; keeping it constant means re-importing updates the same
# deck instead of creating a second one.
DECK_ID = 1758295000

ROOT_CARD = {
    "name": "ALB-RootFamily",
    "qfmt": (
        '<div class="root-head">Root <b>{{Root}}</b>'
        ' &middot; family of {{FamilyCount}}</div>'
        '<div class="word">{{Albanian}}</div>'
        '{{FrontSide}}'
    ),
    "afmt": (
        '<div class="root-head">Root <b>{{Root}}</b>'
        ' &middot; family of {{FamilyCount}}</div>'
        '<hr id=answer>'
        '<div class="gloss">{{English}}</div>'
        '{{#Example}}<div class="ex">{{ExampleSq}}<br><i>{{ExampleEn}}</i></div>{{/Example}}'
        '{{#OtherSenses}}<div class="senses">{{OtherSenses}}</div>{{/OtherSenses}}'
        '<div class="meta">{{POS}} &middot; level {{Level}}'
        ' &middot; rank {{Rank}}</div>'
        '{{#Etymology}}<div class="ety">{{Etymology}}</div>{{/Etymology}}'
    ),
    "css": (
        ".card{font-size:20px;text-align:center;color:#1a1a1a;"
        "background:#fbfbf7;padding:24px}"
        ".root-head{font-size:13px;color:#6b7280;margin-bottom:18px}"
        ".word{font-size:40px;font-weight:600;letter-spacing:.5px}"
        ".gloss{font-size:24px;color:#14532d;margin:10px 0}"
        ".ex{margin:18px auto;max-width:34em;font-size:16px;color:#374151;"
        "border-left:3px solid #d1d5db;padding-left:12px;text-align:left}"
        ".senses{margin:16px auto;max-width:34em;font-size:14px;color:#4b5563;"
        "text-align:left}"
        ".meta{margin-top:18px;font-size:12px;color:#9ca3af}"
        ".ety{margin-top:10px;font-size:12px;color:#6b7280;font-style:italic}"
    ),
}


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def level_files():
    return sorted(
        (f for f in os.listdir(DATA) if f.endswith(".json")),
        # numeric, not lexicographic: level_100 sorts before level_11 otherwise
        key=lambda f: int(re.search(r"(\d+)", f).group(1)),
    )


def main():
    files = level_files()
    if not files:
        print("no level files - run build_course.py first", file=sys.stderr)
        return 1

    model = genanki.Model(DECK_ID, ROOT_CARD["name"],
                          fields=[
                              {"name": "Albanian"},
                              {"name": "English"},
                              {"name": "POS"},
                              {"name": "Root"},
                              {"name": "FamilyCount"},
                              {"name": "Level"},
                              {"name": "Rank"},
                              {"name": "Example"},
                              {"name": "ExampleSq"},
                              {"name": "ExampleEn"},
                              {"name": "OtherSenses"},
                              {"name": "Etymology"},
                          ],
                          templates=[{"qfmt": ROOT_CARD["qfmt"],
                                      "afmt": ROOT_CARD["afmt"]}],
                          css=ROOT_CARD["css"])

    decks = {}
    total = 0
    for fname in files:
        with open(os.path.join(DATA, fname), encoding="utf-8") as fh:
            lvl = json.load(fh)
        n = lvl["level"]
        words = lvl["words"]
        if not words:
            continue

        root = next((w["id"] for w in words if w.get("is_root")), words[0]["id"])
        # One deck per level, named for the root it teaches.
        deck_name = "Albanian L%02d - root %s" % (n, root)
        deck = genanki.Deck(DECK_ID + n, deck_name)
        decks[n] = deck

        # How many cards share each family in this level, for the header.
        fam_counts = {}
        for w in words:
            fam_counts[w.get("family", w["id"])] = fam_counts.get(
                w.get("family", w["id"]), 0) + 1

        for w in words:
            family = w.get("family", w["id"])
            senses = w.get("sense_detail") or []
            head = w.get("en") or ""
            others = [s["gloss"] for s in senses[1:] if s.get("gloss")]

            ex_sq = ex_en = ""
            for s in senses:
                for e in s.get("examples") or []:
                    if isinstance(e, dict) and (e.get("en") or "").strip():
                        ex_sq, ex_en = e.get("sq", ""), e["en"]
                        break
                if ex_en:
                    break

            note = genanki.Note(
                model=model,
                fields=[
                    w["sq"],
                    head,
                    ", ".join(dict.fromkeys(w.get("pos_labels") or [])),
                    root,
                    str(fam_counts.get(family, 1)),
                    str(n),
                    str(w.get("rank") or ""),
                    "1" if ex_en else "",
                    esc(ex_sq),
                    esc(ex_en),
                    esc("; ".join(others[:3])),
                    esc(w.get("etymology") or ""),
                ],
                # Deterministic guid so a re-export updates the same note
                # instead of duplicating it on every rebuild.
                guid=f"albcourse::{w['id']}",
                tags=["albanian", "level%02d" % n, "root_%s" % root,
                      "fam_%s" % family],
            )
            deck.add_note(note)
            total += 1

    pkg = genanki.Package(decks.values())
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, "albanian-roots-families.apkg")
    pkg.write_to_file(out)

    size = os.path.getsize(out)
    print("wrote %s" % os.path.relpath(out, ROOT))
    print("  decks:  %d (one per level)" % len(decks))
    print("  notes:  %d" % total)
    print("  size:   %.1f MB" % (size / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
