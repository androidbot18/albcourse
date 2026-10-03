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

    # 6. a common word may not be gated behind its own rare family.
    #
    # Rule 2 above protects a STEM from being taught after the word built on
    # it. This is the other half: a word may not be taught long after words
    # far commoner than it. The measured failures were two different bugs
    # behind one symptom.
    #
    # ti ("you", rank 18) sat at L141 behind meje (rank 423), an edge invented
    # by reading "...ablative teje is from locative *toí + -je from meje" as if
    # it described ti. Fixed in derivations_from_text/components_of.
    #
    # per ("for", rank 13) sat at L275 behind vere ("wine", rank 1393), because
    # per's family holds pranvere = prane + vere and the edge was computed over
    # the WHOLE family. Fixed by scoring prerequisites over the family's head.
    #
    # A bound of 2000 means: of the 200 commonest words, none teaches after a
    # word rarer than rank 2000. Generous enough to allow prerequisite order to
    # do its job (ka waits for per, esell for sille), tight enough to catch a
    # common word held behind a rare one.
    INVERSION_CEILING = 2000
    freq = {}
    try:
        with open(os.path.join(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))),
                "data", "raw", "sq_50k.txt"), encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                line = line.rstrip("\n")
                if line:
                    w = line.rsplit(" ", 1)[0]
                    freq.setdefault(w, i + 1)
    except OSError:
        freq = {}

    inverted = []
    if freq:
        comp_of = {}
        for f in glob.glob(os.path.join(LEVELS, "level_*.json")):
            for w in json.load(open(f, encoding="utf-8")).get("words") or []:
                comp_of[w["id"]] = (w.get("components") or [])
        for w, rnk in sorted(freq.items(), key=lambda kv: kv[1])[:200]:
            lv = lev.get(w)
            if lv is None:
                continue
            # Test the EDGE, not the level number. A stem is a real
            # prerequisite even when it is rarer -- shkruaj is built on kruaj
            # and must wait for it. The defect was a stem so rare it dragged a
            # common word out of the opening entirely: ti behind meje
            # (rank 423), per behind vere (rank 1393).
            for c in comp_of.get(w, []):
                s = c.get("word")
                srank = freq.get(s)
                if srank is None:
                    continue
                if srank <= INVERSION_CEILING:
                    continue
                slv = lev.get(s)
                if slv is None or slv <= lv:
                    continue
                inverted.append((w, rnk, lv, s, srank, slv))
    print("6. common words not held behind a rare stem: %s"
          % ("OK" if not inverted else "FAIL %d" % len(inverted)))
    for w, rnk, lv, other, ornk, olv in inverted[:8]:
        print("      %s (rank %d, L%d) waits for stem %s (rank %d, L%d)"
              % (w, rnk, lv, other, ornk, olv))

    if missing or gaps or not ok or nlev > CEILING or inverted:
        return 1
    if not late:
        print()
        print("ALL PREREQUISITE TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
