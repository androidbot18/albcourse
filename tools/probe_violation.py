"""Show exactly which stem-after-word violations exist in the shipped data.

test_teaching_order.py flags levels whose word depends on a stem taught in a
LATER level. This prints the pairs, so the cause can be identified rather
than guessed at.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS = os.path.join(ROOT, "data", "levels")
WORDS = os.path.join(ROOT, "data", "words.json")


def main():
    files = sorted(
        (f for f in os.listdir(LEVELS) if f.endswith(".json")),
        key=lambda f: int(re.search(r"(\d+)", f).group(1)),
    )
    level_of = {}
    fam_of = {}
    for i, fname in enumerate(files, 1):
        lvl = json.load(open(os.path.join(LEVELS, fname), encoding="utf-8"))
        for w in lvl["words"]:
            level_of[w["sq"]] = i
        for f in lvl["families"]:
            fam_of[f] = f

    flat = json.load(open(WORDS, encoding="utf-8"))["words"]
    by_word = {w["sq"]: w for w in flat}

    bad = []
    for w in flat:
        for c in (w.get("components") or []):
            if c.get("role") != "stem":
                continue
            stem = c["word"]
            if stem not in level_of:
                continue
            if level_of[stem] > level_of[w["sq"]]:
                bad.append((w["sq"], level_of[w["sq"]], stem,
                            level_of[stem], w.get("family"),
                            fam_of.get(w["sq"])))
    if not bad:
        print("no stem-after-word violations")
        return 0
    print("violations: %d" % len(bad))
    for word, wl, stem, sl, f, fam in sorted(bad, key=lambda b: b[1]):
        print("  L%-4d %-14s needs stem %-12s which is on L%d  (family %s)"
              % (wl, word, stem, sl, fam))
    return 0


if __name__ == "__main__":
    sys.exit(main())
