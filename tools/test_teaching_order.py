#!/usr/bin/env python3
"""Teaching-order guards.

Two things are checked here, both against the SHIPPED data:

  1. Within a level, words are ordered by teaching tier then frequency, so a
     verb family opens with its present tense rather than its rare perfect.
  2. `jam` is the concrete case that motivated the change. It is asserted
     explicitly by name, because a general invariant can hold while the
     specific word the learner complained about stays wrong.

The negative control re-sorts level 2 back by raw rank and confirms the
checks fail. Without it these assertions could pass vacuously, which is how
a no-op sort survived a full build earlier in this project.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
import teaching_order

LEVELS = os.path.join(ROOT, "data", "levels")
WORD = "është"

fails = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def load(n):
    p = os.path.join(LEVELS, "level_%03d.json" % n)
    return json.load(open(p, encoding="utf-8"))


def key(w):
    return (teaching_order.teaching_tier({"senses": [{"gloss": w["en"]}]}),
            w["rank"])


print("teaching order within levels")
bad = []
for n in range(1, 593):
    words = load(n)["words"]
    ks = [key(w) for w in words]
    if ks != sorted(ks):
        bad.append(n)
check(not bad, "all 592 levels in teaching order (bad: %s)" % bad[:6])

print("the jam family specifically")
l2 = load(2)
ids2 = [w["id"] for w in l2["words"]]
check(l2["root"] == "jam", "level 2 is the jam family (root=%s)" % l2["root"])
check(ids2[0] == WORD, "level 2 opens with %r (got %r)" % (WORD, ids2[0]))

# The rare perfect/imperfect forms must have moved out of the opening session.
late = {"qenë", "isha", "jesh", "ishe", "ishin", "jem", "jenë", "ishim",
        "ishit", "qeshë"}
present_late = sorted(late & set(ids2))
check(not present_late,
      "no subjunctive/imperfect form in level 2 (leaked: %s)" % present_late)

# ...and the present tense must actually be there.
present_here = {"është", "jam", "je", "janë", "jemi", "jeni", "qoftë",
                "qenka", "qenke"}
check(len(present_here & set(ids2)) >= 7,
      "level 2 leads with present-tense forms (%d of 9)"
      % len(present_here & set(ids2)))

print("NEGATIVE CONTROL: reorder a level that actually mixes tiers")
# Level 2 is now all tier 0, so mis-ordering it is impossible and it proved
# nothing. Level 3 is where the deferred `jam` forms landed, so it is the
# level that can demonstrate the invariant catching a regression.
l3 = load(3)
ids_real = [w["id"] for w in l3["words"]]
check(teaching_order.teaching_tier(
          {"senses": [{"gloss": l3["words"][0]["en"]}]}) == 0,
      "control: level 3 leads with a tier-0 form (%r)" % ids_real[0])

# Now simulate the pre-fix order: a deferred form pulled to the front.
rare = next(w for w in l3["words"] if w["id"] == "isha")
broken = [rare] + [w for w in l3["words"] if w["id"] != "isha"]
ks = [key(w) for w in broken]
check([w["id"] for w in broken][0] == "isha",
      "control: imperfect 'isha' forced to the front")
check(ks != sorted(ks),
      "control: that order violates the teaching invariant")

# And the shipped file must still pass, so the control is not just asserting
# that some ordering fails -- it is asserting THIS ordering holds.
check([key(w) for w in l3["words"]] == sorted(key(w) for w in l3["words"]),
      "control: the real level 3 still passes")

if fails:
    print("\n%d FAILURE(S)" % len(fails))
    sys.exit(1)
print("\nTEACHING ORDER VERIFIED")
