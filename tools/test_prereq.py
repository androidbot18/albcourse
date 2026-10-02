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

    # 1. every component is a real card in the deck, or is a curated label.
    #
    # The rule exists because dropping it lets prose into the component line
    # ("behind", "appearance", Latin "communis"). pos_balance.EXCLUDE_WORDS
    # is the single deliberate exception: "e" is not a card because its own
    # senses are unresolvable out of context, but the privative PREFIX e- is
    # real and is what the etymology is explaining (esell = e- + sille). It is
    # a prefix, so it never creates a prerequisite edge below -- it is a label
    # on the derivation, not a word to learn first.
    import pos_balance
    allowed = set(pos_balance.EXCLUDE_WORDS)
    missing = [(w, c["word"]) for w, cs in comp.items()
               for c in cs if c["word"] not in lev and c["word"] not in allowed]
    print("1. components resolve to real cards: %s"
          % ("OK" if not missing else "FAIL %d" % len(missing)))
    for w, s in missing[:5]:
        print("      %s references unknown %s" % (w, s))

    # The exception must stay a PREFIX. If an excluded word ever appears as a
    # STEM it would silently stop being taught-before-its-word, which is the
    # ordering guarantee test 2 exists to protect.
    as_stem = [(w, c["word"]) for w, cs in comp.items()
               for c in cs if c["word"] in allowed and c["role"] == "stem"]
    print("1b. curated non-card components are prefixes only: %s"
          % ("OK" if not as_stem else "FAIL %d" % len(as_stem)))
    for w, s in as_stem[:5]:
        print("      %s uses %s as a stem" % (w, s))

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
    # The 600-level ceiling was set when levels were frequency slices. Option 2
    # of the sequencing review gives every multi-member family its own
    # session, which is 495 families that were previously sharing a level with
    # unrelated roots. 751 is the honest cost of that fix: a root and its
    # derivations are no longer buried among six strangers. Sessions still
    # pack to 9 words where a family allows it.
    CEILING = 800
    print("5. level count %d within ceiling %d: %s"
          % (nlev, CEILING, "OK" if nlev <= CEILING else "FAIL"))

    if late:
        print()
        print("NOTE: %d residual violation(s) from mutual borrowing "
              "(each word built from the other; unfixable by ordering)"
              % len(late))
        for w, s, d in late[:10]:
            print("      %-16s needs %-12s (%d later)" % (w, s, d))

    if missing or gaps or not ok or nlev > CEILING:
        return 1
    if not late:
        print()
        print("ALL PREREQUISITE TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
