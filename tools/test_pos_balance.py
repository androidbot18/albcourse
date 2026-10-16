"""The opening levels must teach nouns, not just verbs.

Item 4. Levels 1-10 were 9% noun and 55% verb: a learner's first contact with
the language was almost entirely function words and conjugations, with the
pictureable vocabulary that makes a language stick arriving hundreds of levels
later.

The first two attempts at the fix both failed and both are pinned here, so the
regression cannot come back quietly:

  * The rule tested 'noun in card[\'pos\']'. That is the union of every sense,
    so it called `dhe` ('and') and `une` ('I') nouns and promoted function
    words as if they were concrete vocabulary.
  * The rule then set score=0 on each promoted root, which is not an
    interleaving. It displaced every other family and produced an opening that
    was 88.8% nouns with `te` and `nuk` demoted to level 9 -- worse than the
    problem. The current implementation gives each promoted noun a fractional
    rank between its natural neighbours.
"""
import glob
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pos_balance as pb

ROOT = os.path.dirname(HERE)
LEVELS = os.path.join(ROOT, "data", "levels")

fails = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def load_all():
    files = sorted(glob.glob(os.path.join(LEVELS, "level_*.json")),
                   key=lambda f: int(re.search(r"(\d+)", f).group(1)))
    cards, levels = {}, {}
    for i, f in enumerate(files, 1):
        lvl = json.load(open(f, encoding="utf-8"))
        for w in lvl["words"]:
            cards[w["sq"]] = w
            levels[w["sq"]] = i
    return files, cards, levels


files, cards, levels = load_all()

# The first levels are now hand-curated by theme (tools/opening_levels.py),
# and the noun rebalance acts on the scheduler's levels after them. Both
# must hold the balance: the curated opening as a whole (it has its own
# syllabus, so numbers and pronouns crowd its first ten levels on purpose),
# and the scheduler's first EARLY_LEVELS levels, which is where the
# rebalance is measured.
shipped = [json.load(open(f, encoding="utf-8")) for f in files]
curated = [L for L in shipped if L.get("opening")]
sched = [L for L in shipped if not L.get("opening")][:pb.EARLY_LEVELS]

for name, block in (("curated opening (%d levels)" % len(curated), curated),
                    ("scheduler's first %d levels" % pb.EARLY_LEVELS, sched)):
    mix = Counter(pb.headline_pos(cards[w["sq"]])
                  for L in block for w in L["words"])
    total = sum(mix.values()) or 1
    nshare = mix["noun"] / float(total)
    vshare = mix["verb"] / float(total)
    print("%s: %d words, nouns %.1f%%, verbs %.1f%%"
          % (name, total, 100 * nshare, 100 * vshare))
    check(nshare >= 0.25,
          "%s is at least 25%% noun (got %.1f%%)" % (name, 100 * nshare))
    check(nshare <= 0.60,
          "%s is not a noun wall (got %.1f%%, over 60%%)"
          % (name, 100 * nshare))
    check(vshare <= 0.60,
          "%s is not all verb (got %.1f%%)" % (name, 100 * vshare))
check(bool(curated), "the deck opens with curated levels")

# The demotion regression: score=0 pushed these out of the opening entirely.
# A promoted noun must not be able to cost a function word its place.
# `të` was on this list and is now deliberately OFF it: it is the
# rank-1 token and a conjunction marking the subjunctive, and grammar is
# taught in a separate course. See opening_policy.OPENING_FUNCTION_WORDS
# for the named set that replaces it, and test_opening_policy.py for the
# rule. The other three stay: they are ordinary first-week vocabulary.
for w in ("nuk", "dhe", "unë"):
    check(levels.get(w, 99) <= pb.EARLY_LEVELS,
          "%r still teaches in the first %d levels (on L%s)"
          % (w, pb.EARLY_LEVELS, levels.get(w, "absent")))

# `të` must still be TAUGHT, just later. A policy that dropped it
# from the course would pass every check above.
check(levels.get("të", 0) > pb.EARLY_LEVELS,
      "'të' is deferred, not dropped (on L%s)"
      % levels.get("të", "absent"))

# The promoted nouns must be actual everyday nouns, not the first version's
# picks. Each of these was in that list and is now refused.
print("refused specialist/cultural/abstract nouns")
for w in ("eshtë", "sheh", "bej", "akoma", "shkuar", "kem"):
    check(not pb.is_pictureable_noun(cards[w]),
          "%r (%s) is not promoted"
          % (w, (cards[w].get("en") or "")[:28]))

print("kept everyday nouns")
for w in ("babi", "mami", "nënë", "makinë", "këmbë", "mëngjes"):
    check(pb.is_pictureable_noun(cards[w]),
          "%r (%s) is pictureable"
          % (w, (cards[w].get("en") or "")[:28]))

# The union-POS bug: these have a noun sense but are not nouns.
print("headline POS, not the sense union")
for w in ("dhe", "unë", "ka", "atë"):
    check(pb.headline_pos(cards[w]) != "noun",
          "%r is not treated as a noun (%s)"
          % (w, pb.headline_pos(cards[w])))

print("spread() interleaves rather than prepends")
natural = ["a%d" % i for i in range(20)]
chosen = ["n%d" % i for i in range(6)]
out = pb.spread(chosen, natural)


def skey(r):
    return (out[r], 0) if r in out else (float(natural.index(r)), 1)


merged = sorted(natural + chosen, key=skey)
for n in (5, 10, 20):
    share = sum(1 for r in merged[:n] if r[0] == "n") / float(n)
    check(abs(share - pb.TARGET_NOUN_SHARE) < 0.12,
          "noun share of first %d is %.2f (target %.2f)"
          % (n, share, pb.TARGET_NOUN_SHARE))
check(merged[1] == "a0", "a0 stays near the front (got %r at index 1)" % merged[1])
check(sum(1 for r in merged[:6] if r[0] == "n") <= 2,
      "no noun wall at the front of the merged order")

print("negative control: reverting to score=0 displaces the opening")
# Reproduce the regression: pinning every chosen root to the front.
front = sorted(natural + chosen,
                key=lambda r: (0 if r in chosen else 1,
                               natural.index(r) if r in natural else -1))
front_share = sum(1 for r in front[:6] if r[0] == "n") / 6.0
check(front_share > 0.6,
      "control: prepending gives a %.0f%% noun wall (not a valid fix)"
      % (100 * front_share))

print()
if fails:
    print("FAILURES (%d):" % len(fails))
    for f in fails:
        print("  x %s" % f)
    sys.exit(1)
print("ALL POS-BALANCE CHECKS PASSED")
