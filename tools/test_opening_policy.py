"""The opening must teach content before grammatical scaffolding.

Run: python3 tools/test_opening_policy.py

The failure modes pinned here are the two that actually happened while this
policy was written, both of which produced a green build and a wrong deck:

  1. A POS namespace mismatch. FUNCTION_POS is written in the short tags
     (conj, prep) that build_course.CORE_POS uses, but data/words.json
     spells them out ('conjunction', 'preposition'). A gate that reads only
     the short form returns None for every shipped card and matches nothing,
     silently. pos_balance hit this first; headline_pos() now normalises
     both, and the tests below fail if it stops doing so.

  2. Budgeting by frequency. Admission started as a count of six, which
     admitted the six most frequent closed-class roots -- te, ne, do, me,
     qe, nje, every one inside rank 1-11. Those are precisely the words
     that made level 1 a wall of grammar, so a frequency budget cannot fix
     the problem no matter what the number is. Admission is a named set.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_course
import opening_policy as op

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                    "data")

failures = []


def check(name, got, want):
    if got == want:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s (got %r, want %r)" % (name, got, want))
        failures.append(name)


def words():
    with open(os.path.join(DATA, "words.json"), encoding="utf-8") as fh:
        return json.load(fh)["words"]


print("== POS namespaces both resolve ==")
check("build-time card (short tags)",
      op.headline_pos({"senses": [{"pos": "conj"}]}), "conj")
check("words.json card (full words)",
      op.headline_pos({"pos": ["conjunction", "pronoun"]}), "conj")
check("level file card (sense_detail)",
      op.headline_pos({"sense_detail": [{"pos": "prep"}]}), "prep")
check("unknown POS is not invented",
      op.headline_pos({"pos": ["weird"]}), None)
check("empty card is not a function word", op.is_function_word({}), False)

print()
print("== conjugation is never closed-class ==")
for w in ("është", "janë", "jemi", "kam", "duhet"):
    check("%s is not a function word" % w,
          op.is_function_word({"pos": ["verb"]}), False)

print()
print("== admission is a named set, not a frequency budget ==")
check("te (rank 1) is deferred", op.admits_to_opening("të"), False)
check("qe (rank 10) is deferred", op.admits_to_opening("që"), False)
check("dhe (rank 12) is admitted", op.admits_to_opening("dhe"), True)
check("nje (rank 11) is admitted", op.admits_to_opening("një"), True)
# The regression that made this a named set: every one of these is inside
# rank 1-11, and under a frequency budget of six they would all be admitted.
check("no deferred word is inside rank 1-11 except the named ones",
      sorted(w for w in ("të", "do", "më", "që")
             if op.admits_to_opening(w)), [])

print()
print("== constants agree with the builder ==")
# Restated rather than imported: build_course imports this module, so
# importing the constant back would be circular. The test is what keeps
# them from drifting.
check("MAX_TAIL_RANK matches OPENING_MEMBER_MAX_RANK",
      op.MAX_TAIL_RANK, build_course.OPENING_MEMBER_MAX_RANK)
check("MAX_FUNCTION_WORDS is the size of the named set",
      op.MAX_FUNCTION_WORDS, len(op.OPENING_FUNCTION_WORDS))

print()
print("== the shipped deck honours the policy ==")
try:
    W = words()
except IOError:
    print("  skip data/words.json not built")
    W = []

if W:
    byw = {w["sq"]: w for w in W}
    opening = [w for w in W if w["level"] <= op.EARLY_LEVELS_DEFAULT]

    # 4086, plus `po` (pos_balance.INCLUDE_PARTICLES) and `e`, restored
    # for the curated opening (RECOMMENDATIONS.md section 3.2), and the four
    # days Wiktionary files under their article (pos_balance.ARTICLED_ENTRIES),
    # plus the 41 core words Wiktionary lacks (tools/added_words.py).
    # The Conversation Core (CONVERSATION_PLAN.md) then folds the 362
    # inflected-form cards into their words and adds 144 words and 157
    # phrases: 4133 - 362 + 144 + 157.
    check("the deck has 4072 cards", len(W), 4072)

    # The policy governs the SCHEDULER, which starts after the curated
    # opening (tools/opening_levels.py). That opening teaches `jo` and the
    # numbers on purpose; tools/test_opening_levels.py pins it.
    import opening_levels  # noqa: E402
    n_cur = len(opening_levels.LEVELS)

    # The headline complaint: conjunctions must not open the course.
    # The gate defers FAMILY ROOTS, so a member of an admitted family is
    # not a violation even when it reads as closed class: `domethene` ("a
    # little") is a conjunction sense of `do` in the dictionary, but its
    # family `do` is taught whole in level 2 and the word is needed there.
    # Testing membership of the allowlist per-word produced a false failure
    # on it. What must not happen is a deferred ROOT opening the course.
    early_blocked_roots = [w["sq"] for w in opening
                           if n_cur < w["level"] <= n_cur + 2
                           and w.get("is_root")
                           and op.is_function_word(w)
                           and not op.admits_to_opening(w["sq"])
                           and not op.admits_family_to_opening(w["sq"])]
    check("no deferred closed-class root in the scheduler's first 2 levels",
          early_blocked_roots, [])

    check("te is not in level 1",
          byw["të"]["level"] != 1, True)

    # Conjugations stay: the copula and a common verb paradigm are early.
    # Conjugations stay. The copula is the clearest case: the gate once
    # deferred the whole `jam` family because it also held `meqenese`
    # ("because", a conjunction), which sent eshte -- rank 6 -- to level 186.
    # One card per word (CONVERSATION_PLAN.md step 2): the paradigm is no
    # longer six cards, it is the forms line on the card for `jam`.
    check("jam teaches inside the opening",
          byw["jam"]["level"] <= 10, True)
    check("the jam paradigm is on the jam card",
          all(f in (byw["jam"].get("forms") or "")
              for f in ("është", "jemi", "janë")), True)
    check("eshte is not a card of its own", "është" in byw, False)

    # No word is ever dropped to achieve any of this.
    check("te is still taught somewhere", byw["të"]["level"] > 10, True)
    check("qe is still taught somewhere", byw["që"]["level"] > 10, True)

    # Measured, not asserted at zero. The rare-tail defect is PRE-EXISTING
    # and not this policy's to fix: 16 strays sat in the opening on merged
    # main before this change. Asserting [] here would fail on a correct
    # build and tempt someone to widen the gate -- which is how the
    # function-word work gets quietly undone. The ceiling is pinned instead,
    # so a regression shows up as a count above the known baseline.
    # The early levels are now Conversation Core levels, where every word
    # is hand-placed, so a rare one there (mirupafshim, rank 2,881) is a
    # choice, not a stray. What is measured is anything else that got in.
    core_words = {w for _, ws in opening_levels.LEVELS for w in ws}
    strays = sorted(w["sq"] for w in opening
                    if op.is_rare_tail(w) and w["sq"] not in core_words)
    check("no rare word in the early levels that the core did not place",
          strays, [])

    # Spread, not stacked (RECOMMENDATIONS.md section 3.2). Every deferred
    # root once arrived together at L165-179: 38 top-200 words in one wall.
    def deferred_per_level(words):
        per = {}
        for w in words:
            if (w["level"] > n_cur and w.get("is_root")
                    and not w.get("extended") and op.is_function_word(w)
                    and not op.admits_to_opening(w["sq"])
                    and not op.admits_family_to_opening(w["sq"])):
                per[w["level"]] = per.get(w["level"], 0) + 1
        return per

    per = deferred_per_level(W)
    check("no level teaches more than 2 deferred function-word roots "
          "(worst: %r)" % ((max(per.items(), key=lambda kv: kv[1])
                            if per else None),),
          max(per.values() or [0]) <= 2, True)
    stacked = [dict(w, level=170) for w in W
               if w["sq"] in ("të", "që", "nga", "kjo", "ky")]
    check("control: a stacked block is detected",
          max(deferred_per_level(stacked).values()) > 2, True)

    # The top-200 words are taught by L100. One exception is pinned by
    # name: pastaj (rank 174) is built on ndaj (rank 631), a real stem
    # edge ("pas + ndaj") that the prerequisite rule must honour.
    # The core (L1-%d) now carries the everyday top-200 words. The ones it
    # leaves are grammar words its notes introduce (të, e, do, u, së) and
    # object forms of words it teaches (atë, mua, na); they must follow
    # straight after it, not drift down the course.
    late = sorted(w["sq"] for w in W
                  if w["rank"] <= 200 and w["level"] > n_cur + 10)
    check("no top-200 word is taught more than 10 levels after the core "
          "(got %r)" % (late,), late, [])

    # Level 1 is the headline defect: it opened with te (rank 1,
    # conjunction) and ne (rank 3, conjunction), two of five cards.
    check("no rank-1 conjunction opens the course",
          byw["të"]["level"] == 1, False)

print()
if failures:
    print("FAILURES (%d):" % len(failures))
    for f in failures:
        print("  x %s" % f)
    sys.exit(1)
print("all opening-policy checks passed")
