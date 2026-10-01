#!/usr/bin/env python3
"""Regression tests for two defects found while auditing the merged build.

1. The perfect note was person-blind: 'they (has done) are' is false English.
   Only third-person singular takes 'has done'; the rest take 'have done'.

2. Nine shipped cards kept raw dictionary phrasing even though the converter
   can rewrite them ('qenë', 'horri', 'vëllezërve', ...). These are the forms
   whose Wiktionary sense is not the FIRST sense of the entry, so the card was
   built from a different gloss than the one the rewrite targets.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import form_gloss  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

passed = [0]
failures = []


def check(cond, msg, detail=""):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)
        if detail:
            print("        got: %r" % (detail,))
    passed[0] += 1
    return cond


LOOKUP = {
    "jam": {"glosses": ["to be"]},
    "bie": {"glosses": ["to fall (off)"]},
    "dua": {"glosses": ["to want"]},
    "kalë": {"glosses": ["horse (Equus caballus)"]},
    "vëlla": {"glosses": ["brother"]},
    "horr": {"glosses": ["vagrant, derelict"]},
}

PERFECT = [
    # A copula takes no perfect note, so the note is absent from these.
    ("third-person singular simple perfect indicative of jam", "jam", "he/she/it is"),
    ("third-person plural simple perfect indicative of jam", "jam", "they are"),
    ("first-person singular simple perfect indicative of jam", "jam", "I am"),
    ("second-person plural simple perfect indicative of jam", "jam", "you (pl) are"),
    # A lexical verb keeps the note, and it agrees with the person.
    ("first-person plural simple perfect indicative of bie", "bie", "we (have done)"),
]


def test_person_agreement():
    print("-- perfect agrees with person --")
    for gloss, lem, expect in PERFECT:
        got = form_gloss.friendly_gloss(gloss, "verb", lem, LOOKUP)
        check(got is not None and expect in got,
              "%s... -> %r" % (gloss[:44], expect), got)
    print("-- no false 'has done' outside third person --")
    for gloss, lem, _ in PERFECT:
        if re.search(r"third-person singular", gloss):
            continue
        got = form_gloss.friendly_gloss(gloss, "verb", lem, LOOKUP) or ""
        check("has done" not in got, "no 'has done' in %r" % gloss[:44], got)
    print("-- a copula never carries the perfect note --")
    for gloss in [g for g, lem, _ in PERFECT if lem == "jam"]:
        got = form_gloss.friendly_gloss(gloss, "verb", "jam", LOOKUP) or ""
        check("have done" not in got and "has done" not in got,
              "no perfect note on a 'be' form: %r" % gloss[:44], got)


# Raw dictionary phrasing: the word-order shapes Wiktionary emits.
RAW = re.compile(
    r"^\s*(?:"
    r"(?:\d*-?(?:first|second|third)-person(?:\s+\w+){0,3})"
    r"|(?:(?:in)?definite|indefinite|vocative|positive)\s+"
    r"(?:masculine|feminine|neuter)?\s*\w*"
    r")\b.*?\bof\b\s+\S+\s*$", re.I)

# 'qete' is deliberately absent. Its Wiktionary entry also has the content
# senses 'quiet' and 'calm, tranquil', so its own meaning wins and its gloss
# must not be replaced by a grammatical reading of a minor sense. That word
# keeping dictionary phrasing is the correct outcome, not a miss.
EXPECTED_SHIPPED = {
    # A copula takes no perfect note: English has no '(have done) are'.
    # 'qenë' used to ship exactly that, which is the nonsense this fixes.
    "qenë": "they are",
    "qeshë": "I am",
    # A lexical verb DOES keep the note, and it agrees with the person.
    "ramë": "we (have done) fall",
    "ranë": "they (have done) fall",
    "doni": "you (pl) want",
    "kali": "the horse, singular",
    "vëllezërve": "the brother, plural",
    "horri": "the vagrant, singular",
}

# The two raw glosses that are CORRECT to leave alone, for different reasons.
# 'qete' also means 'quiet', so its entry is content, not a bare inflection.
# 'neve' is glossed 'us; dative of ne': the semicolon means the gloss states
# its own meaning and then adds grammar. Rewriting it drops the dative reading
# and substitutes the lemma's English ('we'), teaching something the card
# never said.
# 'neve' is deliberately absent from this dict. Its gloss 'us; dative of ne'
# does not match the RAW pattern (the semicolon means the gloss names its own
# meaning), and it must keep the original: rewriting would drop the dative
# reading and substitute the lemma's English ('we'). Pinned separately below.
EXPECTED_KEPT_RAW = {"qetë": "quiet"}


def test_shipped_clean():
    print()
    print("-- no shipped card shows raw dictionary phrasing --")
    path = os.path.join(ROOT, "data", "words.json")
    if not os.path.exists(path):
        print("  skip  data/words.json not built yet")
        return
    with open(path, encoding="utf-8") as fh:
        words = json.load(fh)["words"]
    by_sq = {w["sq"]: w for w in words}

    raw_left = [w["sq"] for w in words if RAW.match(str(w.get("en") or ""))]
    check(sorted(raw_left) == sorted(EXPECTED_KEPT_RAW),
          "only the known content words keep raw phrasing (%d left)" % len(raw_left),
          ", ".join(sorted(raw_left)[:8]))

    for sq, expect in sorted(EXPECTED_SHIPPED.items()):
        got = str((by_sq.get(sq) or {}).get("en") or "")
        check(expect in got, "shipped %s reads %r" % (sq, expect), got)

    # 'neve' must keep the meaning its own gloss stated, not the lemma's.
    neve = str((by_sq.get("neve") or {}).get("en") or "")
    check("us" in neve, "shipped neve keeps its own gloss 'us'", neve)
    check("dative" in neve, "shipped neve keeps the dative reading", neve)
    check(not neve.startswith("we"), "shipped neve is not rewritten to 'we'", neve)


def main():
    test_person_agreement()
    test_shipped_clean()
    print()
    if failures:
        print("FAILURES (%d): %d passed, %d failed"
              % (len(failures), passed[0] - len(failures), len(failures)))
        return 1
    print("ALL %d TESTS PASSED" % passed[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
