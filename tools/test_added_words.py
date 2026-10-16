"""Core words Wiktionary lacks (RECOMMENDATIONS.md section 3.6, rec. 2).

Run as:  python3 tools/test_added_words.py

Pins tools/added_words.py and the form-or-lemma coverage count in
tools/measure_coverage.py:

  * apply() refuses an entry that would shadow a Wiktionary card, a word
    the frequency list lacks, and an example that does not use the word
    (negative controls, on synthetic cards);
  * every entry ships as a card with its reviewed headline and example,
    in the main course, and `falni` joins the family of `fal`;
  * the coverage count reads a form listed with its article ("të gjitha")
    as the token a learner sees ("gjitha").
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import added_words as aw  # noqa: E402
import measure_coverage as mc  # noqa: E402

ROOT = os.path.dirname(HERE)
WORD_RE = re.compile(r"^[a-zA-ZçëÇË]+$")
failures = []


def check(name, ok):
    print("  %s %s" % ("ok  " if ok else "FAIL", name))
    if not ok:
        failures.append(name)


def raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


print("== apply() on synthetic data ==")
freq = {w: (i, 100) for i, w in enumerate(sorted(aw.WORDS), 1)}
cards = []
added = aw.apply(cards, freq, lambda p: p, WORD_RE)
check("every entry becomes a card", sorted(added) == sorted(aw.WORDS))
by = {c["word"]: c for c in cards}
check("the headline is the first listed sense",
      all(by[w]["senses"][0]["gloss"] == e["senses"][0]
          for w, e in aw.WORDS.items()))
check("each card carries its reviewed example, highlighted",
      all(by[w]["senses"][0]["examples"][0]["sq"] == e["ex"][0]
          and by[w]["senses"][0]["examples"][0]["offsets"]
          for w, e in aw.WORDS.items()))
off = by["tmerrshëm"]["senses"][0]["examples"][0]
check("a form in the example is highlighted (e tmerrshme)",
      off["sq"][off["offsets"][0][0]:off["offsets"][0][1]] == "tmerrshme")
check("form_of marks the card as a form of its lemma",
      by["falni"]["senses"][0].get("is_form_of") == "fal")
check("control: an entry may not shadow a Wiktionary card",
      raises(lambda: aw.apply([{"word": "pra", "rank": 1}], freq,
                              lambda p: p, WORD_RE)))
check("control: a word the frequency list lacks is refused",
      raises(lambda: aw.apply([], {}, lambda p: p, WORD_RE)))
saved = aw.WORDS["pra"]
aw.WORDS["pra"] = dict(saved, ex=("Nesër shkojmë.", "We go tomorrow."))
check("control: an example that does not use the word is refused",
      raises(lambda: aw.apply([], freq, lambda p: p, WORD_RE)))
aw.WORDS["pra"] = saved

print("\n== shipped data ==")
words_path = os.path.join(ROOT, "data", "words.json")
W = {w["sq"]: w for w in json.load(open(words_path, encoding="utf-8"))["words"]}
missing = sorted(set(aw.WORDS) - set(W))
check("every added word is in the deck (missing: %s)" % missing, not missing)
check("each ships its reviewed headline",
      all(W[w]["en"] == e["senses"][0] for w, e in aw.WORDS.items()
          if w in W))
check("each ships its reviewed example",
      all((W[w].get("ex") or {}).get("sq") == e["ex"][0]
          for w, e in aw.WORDS.items() if w in W))
ext = sorted(w for w in aw.WORDS if w in W and W[w].get("extended"))
check("all are in the main course (extended: %s)" % ext, not ext)
check("falni is taught in the family of fal",
      W.get("falni", {}).get("family") == "fal"
      and W["falni"]["level"] >= W["fal"]["level"])
check("mirupafshim is in the curated opening (L%s)"
      % W.get("mirupafshim", {}).get("level"),
      W.get("mirupafshim", {}).get("level", 99) <= 3)

print("\n== coverage counting ==")
if not os.path.exists(mc.DICT_PATH):
    print("  skip data/raw not present")
else:
    lemmas_of = mc.lemma_index()
    check("'të gjitha' counts as a form of gjithë",
          "gjithë" in lemmas_of.get("gjitha", ()))
    check("'e rëndësishme' counts as a form of rëndësishëm",
          "rëndësishëm" in lemmas_of.get("rëndësishme", ()))
    check("an added word's forms count (problemi -> problem)",
          "problem" in lemmas_of.get("problemi", ()))
    check("control: a multi-word phrase is not a token's form",
          not any(" " in f for f in lemmas_of))
    count = {"gjitha": 3, "gjithë": 1, "x": 4}
    check("form-or-lemma counts the form, exact form does not",
          mc.coverage({"gjithë"}, count, lemmas_of) == 0.5
          and mc.coverage({"gjithë"}, count) == 0.125)

print()
if failures:
    print("FAILURES (%d):" % len(failures))
    for f in failures:
        print("  x " + f)
    sys.exit(1)
print("ALL ADDED-WORD CHECKS PASSED")
