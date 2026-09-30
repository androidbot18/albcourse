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

early = [sq for f in files[:pb.EARLY_LEVELS]
         for sq in [w["sq"] for w in json.load(open(f, encoding="utf-8"))["words"]]]
mix = Counter(pb.headline_pos(cards[sq]) for sq in early)
total = sum(mix.values()) or 1
nshare = mix["noun"] / float(total)
vshare = mix["verb"] / float(total)

print("levels 1-%d: %d words, nouns %.1f%%, verbs %.1f%%"
      % (pb.EARLY_LEVELS, total, 100 * nshare, 100 * vshare))

check(nshare >= 0.25,
      "opening is at least 25%% noun (got %.1f%%)" % (100 * nshare))
check(nshare <= 0.60,
      "opening is not a noun wall (got %.1f%%, over 60%%)" % (100 * nshare))
check(vshare <= 0.60,
      "opening is not all verb (got %.1f%%)" % (100 * vshare))

# The demotion regression: score=0 pushed these out of the opening entirely.
# A promoted noun must not be able to cost a function word its place.
for w in ("të", "nuk", "dhe", "unë"):
    check(levels.get(w, 99) <= pb.EARLY_LEVELS,
          "%r still teaches in the first %d levels (on L%s)"
          % (w, pb.EARLY_LEVELS, levels.get(w, "absent")))

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
