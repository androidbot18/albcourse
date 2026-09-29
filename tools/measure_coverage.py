#!/usr/bin/env python3
"""How much real Albanian text does the deck actually cover?

The question behind the Joyo suggestion: can a course of common vocabulary
reach the ~96% of modern text that Joyo kanji reach in Japanese? That needs
real text, not a word list, so this scores the deck against the
human-translated corpora we already draw examples from.

Two numbers, and they are different things:

  * TYPE COVERAGE  - share of distinct word types the deck knows
  * TOKEN COVERAGE - share of all word occurrences the deck knows

Joyo-style figures are usually quoted for TYPES. For a learner TOKENS are what
matter: a word covering 2% of every sentence you read is worth far more than
a rare word met once. Both are reported.

The corpora are not clean prose. HPLT is mined wiki text and MaCoCu is subtitle
cues, and both contain runs with no separators at all -- strings like
'nukmundterregullohennderkoheqe', forty characters long, which are not Albanian
words. Counting those as vocabulary types produces a 956,645-type 'language',
which is a measurement artefact rather than a fact about Albanian. Tokens longer
than MAX_LEN are therefore excluded, and the number excluded is reported so the
size of the correction is visible rather than hidden.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOK = re.compile(r"[A-Za-zëËçÇ]+")
# No Albanian word approaches this length; the longest in the deck is far shorter.
MAX_LEN = 25


def main():
    corpus_dir = ROOT / "src_raw" / "opus"
    files = sorted(corpus_dir.glob("*.txt")) if corpus_dir.exists() else []
    if not files:
        print("no corpora in %s - run tools/corpus/fetch_more.py" % corpus_dir)
        return 1

    deck = {w["sq"].lower()
            for w in json.loads((ROOT / "data" / "words.json").read_text(encoding="utf-8"))["words"]}
    print("deck cards: %d" % len(deck))

    types = set()
    total = known = dropped = 0
    uncovered = {}
    for p in files:
        for line in p.open(encoding="utf-8", errors="ignore"):
            # Tab-separated en<->sq; the Albanian side is last.
            parts = line.rstrip("\n").split("\t")
            sq = parts[-1] if len(parts) > 1 else parts[0]
            for t in TOK.findall(sq.lower()):
                if len(t) > MAX_LEN:
                    dropped += 1
                    continue
                total += 1
                types.add(t)
                if t in deck:
                    known += 1
                else:
                    uncovered[t] = uncovered.get(t, 0) + 1

    print()
    print("tokens skipped as corpus noise (>%d chars): %d" % (MAX_LEN, dropped))
    print("distinct word types in text : %d" % len(types))
    print("types the deck teaches      : %d (%.1f%%)"
          % (len(types & deck), 100.0 * len(types & deck) / max(1, len(types))))
    print("real tokens                 : %d" % total)
    print("tokens the deck teaches     : %.1f%%" % (100.0 * known / max(1, total)))

    print()
    print("most frequent UNCOVERED words (a course should not miss these):")
    for w, c in sorted(uncovered.items(), key=lambda kv: -kv[1])[:30]:
        print("   %-18s %d" % (w, c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
