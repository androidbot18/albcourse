#!/usr/bin/env python3
"""Guards on the two selection bugs that shipped broken examples.

Both defects are the same shape: two components disagreed about what counts as
"this card already has an example", so cards were skipped that the app then
rendered with no sentence at all.

  1. select_examples.py counted an example on ANY sense. build_words_index.py
     only accepts one on the headline sense, or a sibling of the SAME part of
     speech. So `mire` (gloss "good", adjective) was marked done because its
     ADVERB sense "well" had an example, and then shipped with none.

  2. The English-side sense guard for `e` passed the article sense. "Dhe kshtu
     ajo do te duket nje e tere." carries an English "and" (from "Dhe" = "And
     so") while the Albanian `e` is the ARTICLE in "a whole", so a card glossed
     "and" showed a sentence with no conjunction in it.

The Albanian sentences below are real corpus lines, not invented examples, so
the gates are tested against the text they actually have to survive.
"""
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "corpus"))

import build_words_index as BWI  # noqa: E402
import select_examples as S  # noqa: E402

failures = []
passed = [0]


def check(cond, name, extra=""):
    if cond:
        passed[0] += 1
        print("  ok %s" % name)
    else:
        print("  x  %s%s" % (name, ("  [%s]" % extra) if extra else ""))
        failures.append(name)


def sq_gate_rejects(sq, word):
    """True if the Albanian-side sense gate rejects this sentence for `word`."""
    low = sq.lower()
    forbid = S.SENSE_FORBID_SQ.get(word)
    if forbid and re.search(forbid, low):
        return True
    marker = S.SENSE_MARKER_SQ.get(word)
    if marker and not re.search(marker, low):
        return True
    return False


def main():
    print("example selection guard tests")

    # -- defect 1: headline sense has no example, sibling POS does ----------
    word = {
        "sq": "mirë",
        "sense_detail": [
            {"pos": "adj", "gloss": "good", "examples": []},
            {
                "pos": "adv",
                "gloss": "well",
                "examples": [
                    {"sq": "S'flas shqip mirë .", "en": "I don't speak Albanian well."}
                ],
            },
        ],
    }
    picked = BWI.sense_pair(word)
    check(picked is None,
          "a sibling-POS example is not borrowed for the headline sense",
          repr(picked))

    # Same card, but the headline sense DOES carry one: it must be used.
    word2 = {
        "sq": "mirë",
        "sense_detail": [
            {"pos": "adj", "gloss": "good",
             "examples": [{"sq": "Është një nxëns i mirë.", "en": "He is a good student."}]},
            {"pos": "adv", "gloss": "well",
             "examples": [{"sq": "S'flas shqip mirë .", "en": "I don't speak Albanian well."}]},
        ],
    }
    got = BWI.sense_pair(word2)
    check(got is not None and got["ex"]["sq"] == "Është një nxëns i mirë.",
          "the headline sense's own example wins",
          repr(got))

    # A same-POS sibling IS a legitimate fallback.
    word3 = {
        "sq": "dhe",
        "sense_detail": [
            {"pos": "conj", "gloss": "and", "examples": []},
            {"pos": "conj", "gloss": "also",
             "examples": [{"sq": "Dhe kjo tregon.", "en": "And it shows."}]},
        ],
    }
    got3 = BWI.sense_pair(word3)
    check(got3 is not None and got3.get("from_sense") is True,
          "a same-POS sibling sense is borrowed and labelled",
          repr(got3))

    # -- defect 2: the article sense of `e` paired with the gloss "and" -----
    bad = "Dhe kështu ajo do të duket një e tërë."
    check(sq_gate_rejects(bad, "e"),
          "the article sense of 'e' is rejected for a conjunction card", bad)
    check(re.search(S.SENSE_GUARD["e"], "And so it will look a whole.", re.I) is not None,
          "the English guard alone would accept it (why the sq gate is needed)")

    for good in [
        "Pastaj lindi një bijë dhe e quajti Dina.",
        "Eberi jetoi tridhjetë e katër vjet dhe lindi djem.",
        "E di pse nuk erdhi.",
    ]:
        check(not sq_gate_rejects(good, "e"),
              "a real conjunction sentence is kept: %s" % good[:36], good)

    print("")
    if failures:
        print("FAILURES (%d): %d passed, %d failed"
              % (len(failures), passed[0] - len(failures), len(failures)))
        return 1
    print("ALL %d TESTS PASSED" % passed[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
