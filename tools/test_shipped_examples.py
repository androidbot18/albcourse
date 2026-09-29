#!/usr/bin/env python3
"""Guard the SHIPPED examples in data/words.json against corpus junk.

This exists because the local suite passed while the live site was serving
'dhe' -> 'CTE dhe STEM.' / 'CTE and STEM.' A technical wiki abbreviation that
passed every language gate, and that SENSE_GUARD could not catch because the
English side genuinely does say 'and'.

It also pins the difference between the two example routes. Wiktionary examples
are hand-authored and are allowed to be any length; corpus examples must be
learner-sized, so a corpus example that is 20 words or unpunctuated is a
selection-gate failure, not a style preference.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORDS = ROOT / "data" / "words.json"
CORPUS_SELECTION = ROOT / "data" / "corpus_examples.json"

TOKEN_RE = re.compile(r"[a-zA-Z\u00eb\u00cb\u00e7\u00c7]+")
TERMINAL = re.compile(r"[.!?][\"'\u2019\u201d)]?$")

# Mirrors tools/corpus/test_techgate.py: file paths, product codes, acronyms.
TECH = re.compile(
    r"/ ?proc ?/|/ ?dev ?/|/ ?usr ?/|/ ?etc ?/|/ ?var ?/|https?://|www\."
    r"|[A-Za-z]:\\\\|\w+\-\w+\||\w+\.\w[a-z]{2,4}\b|/\w+/|\d{2,}"
    r"|\b[A-Z]{2,}\b|\[\d{1,3}\]"
)

fails = []


def ok(cond, name, extra=""):
    if cond:
        print("  ok  " + name)
    else:
        fails.append(name + (("  [" + extra + "]") if extra else ""))
        print("  x   " + name + (("  [" + extra + "]") if extra else ""))


def main():
    words = json.loads(WORDS.read_text(encoding="utf-8"))["words"]
    corpus = json.loads(CORPUS_SELECTION.read_text(encoding="utf-8"))
    with_ex = [w for w in words if w.get("ex")]
    print("cards %d, with example %d (%.1f%%)" %
          (len(words), len(with_ex), 100.0 * len(with_ex) / len(words)))
    print()

    ok(all(w["ex"].get("sq") and w["ex"].get("en") for w in with_ex),
       "every shipped example has both halves")
    keys = set()
    for w in with_ex:
        keys.update(w["ex"].keys())
    ok(keys <= {"sq", "en"}, "examples ship only sq/en", str(sorted(keys)))

    # Corpus examples must be learner-sized. Wiktionary ones are exempt: they
    # are authored by hand and some are genuinely long or are fragments.
    corpus_rows = [(k, v) for k, v in corpus.items()]
    bad_len = [(k, v) for k, v in corpus_rows
               if not 3 <= len(v["sq"].split()) <= 9]
    ok(not bad_len, "every corpus example is 3-9 words", str(len(bad_len)))
    for k, v in bad_len[:4]:
        print("       %-14s %s" % (k, v["sq"][:56]))

    bad_term = [(k, v) for k, v in corpus_rows if not TERMINAL.search(v["sq"].strip())]
    ok(not bad_term, "every corpus example ends in terminal punctuation",
       str(len(bad_term)))
    for k, v in bad_term[:4]:
        print("       %-14s %s" % (k, v["sq"][:56]))

    bad_tech = [(k, v) for k, v in corpus_rows
                if TECH.search(v["sq"] + " " + v["en"])]
    ok(not bad_tech, "no corpus example carries a technical marker", str(len(bad_tech)))
    for k, v in bad_tech[:6]:
        print("       %-14s %-46s | %s" % (k, v["sq"][:44], v["en"][:30]))

    bad_tok = [k for k, v in corpus_rows
               if k.lower() not in TOKEN_RE.findall(v["sq"].lower())]
    ok(not bad_tok, "the taught word appears as its own token", str(len(bad_tok)))
    for k in bad_tok[:4]:
        print("       %s" % k)

    # The card that started this: the English side really does say 'and', so a
    # sense guard alone cannot catch it. Assert on the sentence, not the sense.
    dhe = next((w for w in words if w["sq"] == "dhe"), None)
    if dhe and dhe.get("ex"):
        ok("CTE" not in dhe["ex"]["sq"] and "STEM" not in dhe["ex"]["sq"],
           "'dhe' does not ship a technical sentence",
           dhe["ex"]["sq"])
        ok("and" in dhe["ex"]["en"].lower(),
           "'dhe' example still renders the conjunction", dhe["ex"]["en"])
    else:
        ok(True, "'dhe' has no example (nothing to check)")

    print()
    if fails:
        print("FAILURES (%d)" % len(fails))
        return 1
    print("SHIPPED EXAMPLE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
