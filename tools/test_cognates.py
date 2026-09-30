"""The cognate hook must name a source-language FORM, not a meaning.

Item 3. Three real bugs are pinned here, all found by reading the output
rather than by the tests passing:

  1. `_BARE` was written lowercase `from`, but every etymology in the deck
     starts with capital "From". It therefore never matched -- which is why
     `vijë` ("From Latin via") and `turp` ("From Latin turpis") were refused
     and why the English gloss leaked in through a later pattern instead.
     A regex that cannot match is silent, so nothing failed loudly.
  2. The pattern order put the bare form last, so on
     "From Latin horreo (TO-BE-AFRAID)" the quoted gloss was returned and
     urrej got "from Latin to be afraid". A memory hook has to be a word in
     the source language.
  3. A guard meant to stop that leak was inverted: a genuine form is usually
     followed by the gloss (`horreō (TO-BE-AFRAID)`), so refusing any token
     followed by a quote rejected the correct answer and fell through to the
     wrong one.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cognates as cg

fails = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


# Real etymology text taken from the deck, with the expected form.
CASES = [
    ("From Latin horre\u014d (\u201cto be afraid\u201d); change in meaning also "
     "in Romanian ur\u00ee (\u201cto hate\u201d).", "la", "horre\u014d"),
    ("From Vulgar Latin *soca (\u201crope, cable\u201d) (see Italian soga).",
     "la", "soca"),
    ("From Latin via.", "la", "via"),
    ("From Latin turpis.", "la", "turpis"),
    ("From Latin v\u0113rit\u0101s, v\u0113rit\u0101tem.", "la", "v\u0113rit\u0101s"),
    ("From Ancient Greek \u03bc\u03bf\u03c5\u03c3\u03b9\u03ba\u03ae (mousik\u0113).",
     "el", "\u03bc\u03bf\u03c5\u03c3\u03b9\u03ba\u03ae"),
    ("From Italian promettere (\u201cpromise\u201d). Compare Romanian promite.",
     "it", "promettere"),
]

print("source forms, from real etymology text")
for text, lang, want in CASES:
    got = cg.source_form(text, lang)
    form = got[0] if got else None
    check(form == want, "%-9s -> %r (want %r)" % (lang, form, want))

print("a hook never returns an English gloss")
GLOSSES = ("to be afraid", "sort", "thing", "rope, cable", "coffee",
           "voice", "part")
for text, lang, _ in CASES:
    line = cg.cognate_line("x", text, lang) or ""
    body = line[len("from "):]
    head = body.split(" ", 1)[1] if " " in body else ""
    head = head.split(" (")[0].strip()
    check(head.lower() not in [g.lower() for g in GLOSSES],
          "hook form %r is not an English gloss" % head)

print("no hook is invented when the text names no form")
for text, lang in [("From Ottoman Turkish \u0642\u0627\u0645\u0647 (kama).", "tr"),
                   ("", "la"),
                   (None, "la"),
                   ("From Latin via.", None)]:
    got = cg.source_form(text, lang)
    check(got is None or got[0] not in ("", None),
          "refuses to guess: %r" % (text[:34] if text else text,))

print("line shape matches the component line the deck already uses")
ln = cg.cognate_line("lloj", "From Ancient Greek \u03bb\u03bf\u03b3\u03ae (log\u00ed).", "el")
check(ln is not None and ln.startswith("from Greek "),
      "lloj hook is %r" % ln)

print("the whole deck: hooks are well-formed")
base = os.path.join(os.path.dirname(HERE), "data", "levels")
cards = {}
for f in sorted(glob.glob(os.path.join(base, "level_*.json"))):
    for w in json.load(open(f, encoding="utf-8"))["words"]:
        cards[w["sq"]] = w

withlang = [c for c in cards.values() if c.get("source_lang")]
lines = []
for c in withlang:
    ln = cg.cognate_line(c["sq"], c.get("etymology") or "", c["source_lang"])
    if ln:
        lines.append((c["rank"], c["sq"], ln))

print("  cards with a source language: %d" % len(withlang))
print("  cards with a hook: %d" % len(lines))
check(len(lines) >= 100, "at least 100 hooks (got %d)" % len(lines))

# Every hook must name one of the languages we actually recorded, and must
# not be a bare English word with no source form at all.
bad_lang = [(sq, ln) for _, sq, ln in lines
            if not ln.startswith("from ") or len(ln) < len("from La x")]
check(not bad_lang, "all hooks name a language and a form: %s" % bad_lang[:4])

bad_shape = [(sq, ln) for _, sq, ln in lines
             if ln.count("(") != ln.count(")")]
check(not bad_shape, "balanced parentheses in every hook: %s" % bad_shape[:4])

bad_words = [(sq, ln) for _, sq, ln in lines
             if re.search(r"\b(to be|to have|sort of|the same)\b", ln)]
check(not bad_words, "no hook contains an English verb phrase: %s"
      % bad_words[:4])

print()
if fails:
    print("FAILURES (%d):" % len(fails))
    for f in fails:
        print("  x %s" % f)
    sys.exit(1)
print("ALL COGNATE CHECKS PASSED")
