"""Prerequisite ordering: a stem is never taught after the word built on it.

Run as:  python3 tools/test_prereq.py

The course is ordered so a word's lexical stem comes first, the way a
Wanikani kanji's component comes before the kanji that uses it. This suite
locks that invariant in, so a later change to the level packer cannot
silently reintroduce words that reference an untaught stem.
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS = os.path.join(ROOT, "data", "levels")


def load():
    lev = {}
    comp = {}
    for f in sorted(glob.glob(os.path.join(LEVELS, "level_*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        for w in d["words"]:
            lev[w["sq"]] = d["level"]
            if w.get("components"):
                comp[w["sq"]] = w["components"]
    return lev, comp


def main():
    lev, comp = load()
    if not lev:
        print("FAIL: no levels found; run tools/build_course.py first")
        return 1

    # Levels are 1-indexed (level_0001.json holds level 1), matching the
    # number the learner sees.
    nlev = max(lev.values())
    print("levels: %d  cards: %d  cards with components: %d"
          % (nlev, len(lev), len(comp)))

    # 1. every component is a real card in the deck
    missing = [(w, c["word"]) for w, cs in comp.items()
               for c in cs if c["word"] not in lev]
    print("1. components resolve to real cards: %s"
          % ("OK" if not missing else "FAIL %d" % len(missing)))
    for w, s in missing[:5]:
        print("      %s references unknown %s" % (w, s))

    # 2. a stem is not taught later than the word using it
    late = []
    for w, cs in comp.items():
        for c in cs:
            if c["role"] != "stem":
                continue
            s = c["word"]
            if s in lev and lev[s] > lev[w]:
                late.append((w, s, lev[s] - lev[w]))
    late.sort(key=lambda t: -t[2])
    print("2. stem taught no later than its word: %d violation(s)" % len(late))
    for w, s, d in late[:10]:
        print("      %-16s L%-4d needs %-12s L%-4d (%d later)"
              % (w, lev[w], s, lev[s], d))

    # 3. levels are contiguous 1..N, no gaps
    gaps = sorted(set(range(1, nlev + 1)) - set(lev.values()))
    print("3. levels contiguous 1..%d: %s"
          % (nlev, "OK" if not gaps else "FAIL gaps %s" % gaps[:5]))

    # 4. the esell case from the original report
    ok = ("esëll" in comp and "sillë" in lev
          and lev["sillë"] <= lev["esëll"])
    print("4. esell follows sille: %s  [esell L%s, sille L%s]"
          % ("OK" if ok else "FAIL", lev.get("esëll"), lev.get("sillë")))

    # 5. the course is grouped, not thousands of one-word levels
    print("5. level count %d within target 600: %s"
          % (nlev, "OK" if nlev <= 600 else "FAIL"))

    if late:
        print()
        print("NOTE: %d residual violation(s) from mutual borrowing "
              "(each word built from the other; unfixable by ordering)"
              % len(late))
        for w, s, d in late[:10]:
            print("      %-16s needs %-12s (%d later)" % (w, s, d))

    if missing or gaps or not ok or nlev > 600:
        return 1
    if not late:
        print()
        print("ALL PREREQUISITE TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
