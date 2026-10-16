"""Root first, tail later: a family's rare words wait for their own frequency.

Run as:  python3 tools/test_tail_later.py

A family used to be taught in consecutive levels, so a common root carried
its rare derivatives into the opening: do (rank 4) taught doemos (rank
30516) in level 2, and une ("I", rank 16) was pushed to level 11. Now the
common head is taught on its own frequency and the rare tail comes back as a
later run of levels marked `resumes`.

This pins the rule on a synthetic course (with a negative control showing
the old consecutive placement fails it) and on the shipped deck.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_course as bc  # noqa: E402
import opening_policy as op  # noqa: E402

LEVELS = os.path.join(os.path.dirname(HERE), "data", "levels")
failures = []


def check(name, ok):
    print("  %s %s" % ("ok  " if ok else "FAIL", name))
    if not ok:
        failures.append(name)


def card(word, rank):
    # An adverb: not a pictureable noun (no early-noun boost) and not a
    # closed-class word (no opening deferral), so only frequency decides.
    return {"word": word, "rank": rank,
            "senses": [{"pos": "adv", "pos_label": "adverb",
                        "gloss": word, "tags": []}]}


def synthetic():
    """Root `a` (rank 1) with two rare members, then 60 common singletons."""
    cards = [card("a", 1), card("ax", 5000), card("ay", 5001)]
    families = {"a": ["a", "ax", "ay"]}
    for i in range(60):
        w = "s%02d" % i
        cards.append(card(w, 10 + i))
        families[w] = [w]
    return cards, families


def level_of(levels):
    return {w: i for i, lvl in enumerate(levels, 1) for w in lvl[1]}


print("== synthetic course ==")
cards, families = synthetic()
levels = bc.assign_levels(cards, families)
lv = level_of(levels)
check("the common head is taught first", lv["a"] == 1)
check("the rare tail waits until every more common word is taught",
      lv["ax"] > max(lv["s%02d" % i] for i in range(60)))
tail = levels[lv["ax"] - 1]
check("the tail level resumes its family", tail[6] is True and tail[0] == "a")
check("the tail level is labelled as the family's rarer words",
      tail[2] == "a (rarer words)")
check("nothing is dropped", sorted(lv) == sorted(c["word"] for c in cards))

# Negative control: the old rule placed the tail in the level right after
# its head. The check above must reject that order.
old = [lvl for lvl in levels if lvl is not tail]
old.insert(lv["a"], tail)
olv = level_of(old)
check("control: a tail right after its head is caught",
      not olv["ax"] > max(olv["s%02d" % i] for i in range(60)))

print("\n== shipped deck ==")
files = sorted(glob.glob(os.path.join(LEVELS, "level_*.json")),
               key=lambda f: int(re.search(r"(\d+)\.json$", f).group(1)))
shipped = [json.load(open(f, encoding="utf-8")) for f in files]
if not shipped:
    print("  skip data/levels not built")
else:
    lvl_of = {w["sq"]: L["level"] for L in shipped for w in L["words"]}
    # A curated opening word is there on purpose, whatever its rank
    # (motër "sister", nëntë "nine"): tools/opening_levels.py. What must not
    # happen is a rare word riding its family's root into the opening, so
    # the check is on the scheduler's levels, and on the curated ones it is
    # that nothing but the curated words got in.
    import opening_levels as ol  # noqa: E402
    sched = [L for L in shipped if not L.get("opening")]
    opening = [w for L in sched[:op.EARLY_LEVELS_DEFAULT] for w in L["words"]]
    strays = sorted(w["sq"] for w in opening if op.is_rare_tail(w))
    check("no rare-tail word in the scheduler's first levels (got %s)"
          % strays, not strays)
    listed = {w for _, ws in ol.LEVELS for w in ws}
    extra = sorted(w["sq"] for L in shipped if L.get("opening")
                   for w in L["words"] if w["sq"] not in listed)
    check("curated levels hold only the curated words (got %s)" % extra,
          not extra)
    for w, must in (("doemos", "do"), ("mjaftoj", "me"), ("qeshë", "jam")):
        check("%s waits for its own band, after %s" % (w, must),
              lvl_of[w] > op.EARLY_LEVELS_DEFAULT and lvl_of[w] > lvl_of[must])
    tails = [L for L in shipped if L.get("resumes")]
    check("some families resume later (%d)" % len(tails), bool(tails))
    head_of = {}
    for L in shipped:
        for w in L["words"]:
            head_of.setdefault(w["family"], L["level"])
    check("every resumed family was taught before",
          all(head_of[L["root"]] < L["level"] for L in tails))

print()
if failures:
    print("FAILURES (%d):" % len(failures))
    for f in failures:
        print("  x " + f)
    sys.exit(1)
print("ALL TAIL-LATER CHECKS PASSED")
