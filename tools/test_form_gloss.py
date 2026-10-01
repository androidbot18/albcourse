#!/usr/bin/env python3
"""The learner-facing form-gloss rewrite.

A form card's gloss arrives from Wiktionary as grammar ('third-person singular
present indicative of jam'). This asserts the rewrite is grammatical and keeps
the original whenever it cannot be trusted.

The failure modes are the ones actually found while writing the rewrite, and
each is asserted against real Wiktionary slot strings rather than invented ones:

  * 'he/she/it (used to) was is' - tense and verb were assembled as two fields
    and concatenated, so a past slot got a present form bolted on top.
  * 'the anyone, plural' - njeri is glossed 'anyone' upstream, which is the
    INDEFINITE use; taking a definite ending at face value gave nonsense.
  * 'I (used to) was am' - person and number were separate fields, so a
    first-person PLURAL form rendered its pronoun as 'I'.
  * 'they jam' - 'simple perfect' is an Albanian tense with no English word
    for it, and the unhandled slot fell through to a bare infinitive.
  * 'you (pl)!' - 'indicative/imperative' names two moods at once and must
    claim neither.

These are tested against INPUT strings rather than the shipped cards. Once the
rewrite is running, the deck no longer contains pre-rewrite glosses to find, so
a test that hunts for them silently stops testing anything -- which is exactly
what happened to the first version of this file.

The last block is a sweep over the real data: every shipped form card must be
either a clean rewrite or a verbatim Wiktionary gloss, never a half-converted
string.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import form_gloss as FG  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
failures = []
passed = [0]


def check(cond, name, extra=""):
    if cond:
        passed[0] += 1
        print("  ok %s" % name)
    else:
        print("  x  %s%s" % (name, ("  [%s]" % extra) if extra else ""))
        failures.append(name)


LOOKUP = {
    "jam": {"glosses": ["to be"]},
    "kam": {"glosses": ["to have"]},
    "shkoj": {"glosses": ["to go, pass"]},
    "them": {"glosses": ["to say"]},
    "dua": {"glosses": ["to want"]},
    "vdes": {"glosses": ["to die"]},
    "vij": {"glosses": ["to arrive"]},
    "njeri": {"glosses": ["anyone"]},
    "baba": {"glosses": ["dad, father"]},
    "minutë": {"glosses": ["minute (unit of time)"]},
    "madh": {"glosses": ["big, large"]},
    "sekondë": {"glosses": ["second (unit of time)"]},
    "bytë": {"glosses": ["white"]},
}

# Real Wiktionary slot strings -> the learner-facing gloss each must produce.
CASES = [
    ("third-person singular present indicative of jam", "verb", "jam",
     "he/she/it is (from jam, to be)"),
    ("third-person plural present indicative of jam", "verb", "jam",
     "they are (from jam, to be)"),
    ("second-person singular present indicative of jam", "verb", "jam",
     "you (sg) are (from jam, to be)"),
    ("first-person plural present indicative of kam", "verb", "kam",
     "we have (from kam, to have)"),
    ("second-person singular present indicative of kam", "verb", "kam",
     "you (sg) have (from kam, to have)"),
    ("third-person singular imperfect indicative of jam", "verb", "jam",
     "he/she/it (used to) was (from jam, to be)"),
    ("first-person singular imperfect indicative of jam", "verb", "jam",
     "I (used to) was (from jam, to be)"),
    ("first-person singular aorist indicative of them", "verb", "them",
     "I (once did) said (from them, to say)"),
    # Albanian tenses with no single English word. For a LEXICAL verb the
    # perfect agrees with the person: only third-person singular takes 'has
    # done', the rest take 'have done'.
    ("third-person plural simple perfect indicative of dua", "verb", "dua",
     "they (have done) want (from dua, to want)"),
    # For 'be' the note is dropped entirely. English has no '(have done) are',
    # so attaching the perfect to the copula shipped qenë as 'they (have
    # done) are (from jam, to be)'. The form itself is 'they are', which is
    # true, so the note was the only thing that had to go.
    ("third-person plural simple perfect indicative of jam", "verb", "jam",
     "they are (from jam, to be)"),
    ("third-person singular simple perfect indicative of jam", "verb", "jam",
     "he/she/it is (from jam, to be)"),
    # A gloss that is nothing but the slot. A participle is a word the learner
    # meets, so it is glossed by what it DOES, not by the slot name. This was the
    # largest group of leaks: 91 of the 133 still leaking when measured.
    ("participle of vdes", "verb", "vdes", "die, past form (from vdes, to die)"),
    ("past participle of them", "verb", "them",
     "say, past form (from them, to say)"),
    ("plural of minutë", "noun", "minutë", "minute, plural (from minutë)"),
    # Two moods at once: claim neither.
    ("second-person plural present indicative/imperative of dua", "verb", "dua",
     "you (pl) want (from dua, to want)"),
    # The subjunctive, jussive and conditional have no distinct English word, so
    # a card labelled '(subjunctive)' taught grammar rather than meaning. They
    # render as the infinitive, which is what follows the conjunction 'te'.
    ("third-person singular present subjunctive of them", "verb", "them",
     "he/she/it say (from them, to say)"),
    ("second-person singular present subjunctive of dua", "verb", "dua",
     "you (sg) want (from dua, to want)"),
    # Indicative AND subjunctive together: a mood note would still be a claim
    # about the English form, so none is made.
    ("first-person plural present indicative/subjunctive of dua", "verb", "dua",
     "we want (from dua, to want)"),
    # Nominal endings.
    ("definite nominative plural of njeri", "noun", "njeri",
     "the person, plural (from njeri)"),
    ("indefinite nominative plural of njeri", "noun", "njeri",
     "person, plural (from njeri)"),
    ("definite nominative singular of baba", "noun", "baba",
     "the dad, singular (from baba)"),
    ("feminine singular of madh", "adjective", "madh",
     "big, singular (from madh)"),
    # Imperative is an address, not a statement. The '!' already carries the mood,
    # so the slot name is not repeated: 'you (sg)! (from shkoj, to go)'.
    ("second-person singular imperative of shkoj", "verb", "shkoj",
     "you (sg)! (from shkoj, to go)"),
    # An ambiguous person slot names both rather than guessing.
    ("second/third-person singular present indicative of vij", "verb", "vij",
     "you (sg) or he/she/it arrive (from vij, to arrive)"),
]

DEFECTS = [
    (re.compile(r"\b(was|were|is|are|am)\s+(is|are|am|be)\b", re.I), "two verbs in a row"),
    (re.compile(r"\bthe\s+(anyone|anybody|someone|somebody|nothing|something|anything|everything)\b",
                re.I), "bad article"),
    (re.compile(r"\b(\w+)\s+\1\b", re.I), "duplicated word"),
        # Every grammar term ever found leaking, in one pattern. The list grew
    # each time a residue turned up, so it covers the moods as well as the
    # cases, the persons and the participles: those three groups are what
    # survived the rewrite until the 133 were measured directly.
    (re.compile(r"\bindicative\b|\bnominative\b|\baccusative\b|\bgenitive\b"
                r"|\bablative\b|\bvocative\b|\bdative\b|\bimperfect\b"
                r"|\baorist\b|\bjussive\b|\bsubjunctive\b|\bconditional\b"
                r"|\bimperative\b|\bparticiple\b|\boptative\b"
                r"|\bthird-person\b|\bfirst-person\b|\bsecond-person\b"
                r"|\bmasculine\b|\bfeminine\b|\bdefinite\b|\bindefinite\b"
                r"|\bplural of\b|\bsingular of\b|\bparticiple of\b", re.I),
     "grammar jargon left in"),
    (re.compile(r"\(\s*\)"), "empty parens"),
    (re.compile(r"\s{2,}"), "double space"),
]

# A rewritten gloss always keeps the lemma it came from, so the learner can
# see the base word. This is what separates a rewrite from the original.
_MISSING_TAIL = re.compile(r"\s\(from [A-Za-zëçËÇ][A-Za-zëçËÇ'-]*\)")


def main():
    print("learner-facing form gloss tests")

    # -- the defect checks must be able to fail, or the sweep proves nothing --
    broken = {
        "two verbs in a row": "he/she/it (used to) was is",
        "bad article": "the anyone, plural",
        "duplicated word": "the the person",
        "grammar jargon left in": "he/she/it (subjunctive) say (from them, to say)",
        "empty parens": "the person ()",
        "double space": "the  person",
    }
    for rx, label in DEFECTS:
        check(rx.search(broken[label]) is not None,
              "the %s check can fail" % label)

    # -- the rewrite itself, against real Wiktionary slot strings ------------
    for gloss, pos, lemma, expected in CASES:
        got = FG.friendly_gloss(gloss, pos, lemma, LOOKUP)
        check(got == expected, "%s -> %r" % (lemma, expected), got)

    # -- nothing ungrammatical anywhere in the table -----------------------
    for gloss, pos, lemma, _ in CASES:
        got = FG.friendly_gloss(gloss, pos, lemma, LOOKUP)
        if not got:
            continue
        for rx, label in DEFECTS:
            check(rx.search(got) is None,
                  "clean: %s (%s)" % (got[:44], label), got)

    # -- refusals: keep the original rather than guess ---------------------
    check(FG.friendly_gloss("and", "conj", "dhe", LOOKUP) is None,
          "a non-form gloss is never rewritten")
    check(FG.friendly_gloss("third-person singular present indicative of zzz",
                            "verb", "është", LOOKUP) is None,
          "a pointer to an unknown lemma is left alone")
    check(FG.friendly_gloss("us; dative of ne", "pronoun", "neve", LOOKUP) is None,
          "an archaic dialect gloss is left alone")
    check(FG.friendly_gloss("plural of sekondë", "noun", "sekondë", LOOKUP)
          == "second, plural (from sekondë)",
          "a parenthetical aside is stripped from the display gloss",
          FG.friendly_gloss("plural of sekondë", "noun", "sekondë", LOOKUP))

    # -- sweep the SHIPPED data -------------------------------------------
    # Every form card in the deck must be either fully rewritten or verbatim.
    # A half-converted string is the failure this catches.
    words = json.loads((ROOT / "data" / "words.json").read_text(encoding="utf-8"))["words"]
    PTR = re.compile(r"\bof\s+[A-Za-zëçËÇ][A-Za-zëçËÇ'-]*\s*[.;:]?\s*$")
    still_raw, half = [], []
    for w in words:
        g = str(w.get("en", "")).strip()
        if not PTR.search(g):
            continue
        # A raw gloss has grammar jargon and no '(from lemma)' tail.
        jargon = any(rx.search(g) for rx, _ in DEFECTS[3:4])
        if jargon and not _MISSING_TAIL.search(g):
            still_raw.append(w["sq"])
        elif _MISSING_TAIL.search(g):
            # Rewritten: it must not still be carrying grammar jargon.
            if jargon:
                half.append((w["sq"], g))

    check(not half, "no shipped form gloss is half-converted",
          "; ".join("%s: %s" % (s, g[:40]) for s, g in half[:3]))
    check(len(still_raw) <= 25,
          "at most a couple of dozen form cards keep the raw gloss",
          "%d: %s" % (len(still_raw), ", ".join(still_raw[:8])))

    # The words the user actually complained about, in shipped form.
    by_sq = {w["sq"]: str(w.get("en", "")) for w in words}
    for word, expected in [
        ("është", "he/she/it is (from jam, to be)"),
        ("janë", "they are (from jam, to be)"),
        ("kemi", "we have (from kam, to have)"),
    ]:
        check(by_sq.get(word) == expected,
              "shipped %s reads %r" % (word, expected), by_sq.get(word))
    check(by_sq.get("njerëzit", "").startswith("the "),
          "shipped njerëzit is definite", by_sq.get("njerëzit"))
    check("anyone" not in by_sq.get("njerëzit", ""),
          "shipped njerëzit does not use the indefinite lemma gloss",
          by_sq.get("njerëzit"))

    print()
    if failures:
        print("FAILURES (%d): %d passed, %d failed"
              % (len(failures), passed[0] - len(failures), len(failures)))
        return 1
    print("ALL %d TESTS PASSED" % passed[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
