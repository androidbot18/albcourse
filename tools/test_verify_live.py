#!/usr/bin/env python3
"""Negative control for the deployed 'e' checks in verify_live_merge.py.

The two checks those lines replaced were VACUOUS: both passed on the very
sentence they were written to reject.

    ' e ' in ex            -> true for '...dhe eshte shume e lire.', where
                              that 'e' IS the article.
    'një e tërë' not in ex -> true for any sentence without that one
                              literal phrase, so it never detected the
                              article sense at all.

A test suite that cannot fail is not a test suite. This feeds the real
defect sentence through the same code path the verifier uses and asserts
both checks REJECT it, then asserts a genuine conjunction is ACCEPTED.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "corpus"))
from select_examples import context_ok, article_reading  # noqa: E402

# The exact sentence that shipped under the gloss "and".
DEFECT = "Nuk kërkon shumë kohë dhe është shumë e lirë."
# A genuine conjunction: 'e' joins two clauses, and the following token is a
# verb, not the noun an article would govern.
GOOD = "E marr për kujtesë dhe depresion."


def pos_index_from(words):
    idx = {}
    for w in words:
        for lab in w.get("pos") or []:
            idx.setdefault(w["sq"].lower(), [])
            if lab not in idx[w["sq"].lower()]:
                idx[w["sq"].lower()].append(lab)
    return idx


def main():
    words = json.load(open(ROOT / "data" / "words.json", encoding="utf-8"))["words"]
    pos_index = pos_index_from(words)

    fails = []

    def check(cond, name, extra=""):
        print(("  ok " if cond else "  x  ") + name + ("  [%s]" % extra if extra else ""))
        if not cond:
            fails.append(name)

    print("negative control: the old checks were vacuous")

    # The two OLD assertions, run against the defect. Both must be shown to
    # pass -- that is the whole point: they are why this bug shipped.
    check(" e " in DEFECT, "OLD check 1 passes on the defect (was vacuous)")
    check("një e tërë" not in DEFECT, "OLD check 2 passes on the defect (was vacuous)")

    print()
    print("negative control: the NEW checks must reject it")
    check(not context_ok(DEFECT, "e", pos_index),
          "NEW check 1 rejects the article sentence", DEFECT)
    check(article_reading(DEFECT, "e", pos_index),
          "NEW check 2 detects the article reading", DEFECT)

    print()
    print("and must still accept a genuine conjunction")
    check(context_ok(GOOD, "e", pos_index), "NEW check 1 accepts a real conjunction", GOOD)
    check(not article_reading(GOOD, "e", pos_index),
          "NEW check 2 finds no article reading", GOOD)

    print()
    if fails:
        print("FAILURES: %d" % len(fails))
        return 1
    print("NEGATIVE CONTROL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
