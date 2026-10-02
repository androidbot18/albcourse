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
import json
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


def real_pos_index():
    """POS lookup built from the deck's own level files, as main() does."""
    pos = {}
    for lv in sorted(S.LEVEL_DIR.glob("level_*.json")):
        for w in json.loads(lv.read_text(encoding="utf-8"))["words"]:
            labs = [str(p).lower() for p in (w.get("pos") or [])]
            slot = pos.setdefault(w["sq"].lower(), [])
            for lab in labs:
                if lab not in slot:
                    slot.append(lab)
    return pos


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

    # -- defect 3: a sentence-level guard cannot see a per-token sense ------
    # The shipped 'e' card said "and" and shipped 'Nuk kerkon shume kohe dhe
    # eshte shume e lire.' The English DOES contain "and", so SENSE_GUARD
    # passes it, but the conjunction in that sentence is `dhe`; the `e` is the
    # article in 'shume e lire'. Validating the sentence cannot catch a
    # per-token sense error, which is why context_ok() inspects the Albanian
    # neighbourhood of the token instead.
    pi = real_pos_index()
    shipped = "Nuk kërkon shumë kohë dhe është shumë e lirë."
    check(re.search(S.SENSE_GUARD["e"],
                    "It doesn't require much time and it's extremely "
                    "inexpensive.", re.I) is not None,
          "the sentence-level guard accepts the shipped defect")
    check(not S.context_ok(shipped, "e", pi),
          "context_ok rejects the shipped article reading", shipped)

    for bad, why in [
        ("Dhe kshtu ajo do te duket nje e tere.", "article, unclassifiable head"),
        ("Në rrugën e qytetit", "article before a noun"),
        ("Ka qenë një eksperiencë e re dhe sfiduese.",
         "ambiguous 're' = noun|verb"),
    ]:
        check(not S.context_ok(bad, "e", pi),
              "context_ok rejects %s" % why, bad)

    for good, why in [
        ("A duhet të kthehem e të shërbej atje?", "infinitive marker between"),
        ("Atëherë do të jetoni e nuk do të vdisni.", "auxiliary chain after"),
        ("Ai e ngre kokën dhe më thotë diçka.", "verb follows"),
        ("Edhe e kam gjetur në një fjalor shqip-shqip.", "pronoun follows"),
        ("Gjithsej tridhjetë e një mbretër.", "compound numeral"),
        ("Prej shtëpisë del e shkon në fushë.", "verb follows"),
    ]:
        check(S.context_ok(good, "e", pi),
              "context_ok keeps a real conjunction (%s)" % why, good)

    # The gate must be able to FAIL. A gate that accepted everything would
    # pass every 'keeps' case above while still shipping the original defect.
    check(not S.context_ok("Në rrugën e qytetit", "e", pi),
          "context_ok is not vacuously permissive")

    print("")
    if failures:
        print("FAILURES (%d): %d passed, %d failed"
              % (len(failures), passed[0] - len(failures), len(failures)))
        return 1
    print("ALL %d TESTS PASSED" % passed[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
