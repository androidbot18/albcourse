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
sys.path.insert(0, str(ROOT / "tools"))
import added_words  # noqa: E402

TOK = re.compile(r"[A-Za-zëËçÇ]+")
# No Albanian word approaches this length; the longest in the deck is far shorter.
MAX_LEN = 25
FREQ_PATH = ROOT / "data" / "raw" / "sq_50k.txt"
DICT_PATH = ROOT / "data" / "raw" / "kaikki_albanian.jsonl"
# The linking article and its kin. Wiktionary lists an adjective's forms with
# it ("e rëndësishme", "të gjitha"), but text tokenises it apart, so the
# token a learner reads is the last word.
ARTICLES = {"i", "e", "të", "së"}


# ------------------------------------------------- frequency-list coverage
#
# RECOMMENDATIONS.md section 3.6. The corpora above are not in the repo; the
# pinned frequency list is, so the course's coverage goal is measured
# against it. Two ways to count a token as known:
#
#   exact form     the token is itself a card;
#   form or lemma  the token is a card, or an inflected form of one
#                  (`shkova` when `shkoj` is taught, `të gjitha` when
#                  `gjithë` is).
#
# The second is what a learner who has met the lemma can read. The first
# stops near 70% whatever the deck size, because Albanian inflects.

def frequency_counts(path=FREQ_PATH):
    """{lowercased form: token count} from the frequency list."""
    count = {}
    for line in open(path, encoding="utf-8"):
        w, c = line.rsplit(" ", 1)
        count[w.lower()] = count.get(w.lower(), 0) + int(c)
    return count


def lemma_index(path=DICT_PATH):
    """{form: {lemma, ...}} from Wiktionary's form lists and form-of senses,
    plus the forms tools/added_words.py lists for its hand-added words."""
    lemmas_of = {}

    def add(form, lemma):
        parts = form.lower().split()
        # "të gjitha" -> gjitha; a longer phrase ("do të shkoj") is not one
        # token's form.
        if not parts or any(p not in ARTICLES for p in parts[:-1]):
            return
        lemmas_of.setdefault(parts[-1], set()).add(lemma.lower())

    for line in open(path, encoding="utf-8"):
        j = json.loads(line)
        if j.get("lang_code") != "sq":
            continue
        lemma = j["word"]
        for f in j.get("forms") or []:
            if f.get("form") and not {
                    "table-tags", "inflection-template",
                    "romanization"} & set(f.get("tags") or []):
                add(f["form"], lemma)
        for s in j.get("senses") or []:
            for fo in s.get("form_of") or []:
                if fo.get("word"):
                    add(lemma, fo["word"])
    for form, lemma in added_words.lemma_forms().items():
        add(form, lemma)
    return lemmas_of


def coverage(deck, count, lemmas_of=None):
    """Share of tokens known. With lemmas_of, form-or-lemma; else exact."""
    deck = {w.lower() for w in deck}
    total = sum(count.values())
    known = sum(c for w, c in count.items()
                if w in deck or (lemmas_of and lemmas_of.get(w, set()) & deck))
    return known / total


def uncovered_forms(deck, count, lemmas_of, top=1411):
    """The most frequent forms that no card or card's lemma covers."""
    deck = {w.lower() for w in deck}
    ranked = sorted(count, key=lambda w: -count[w])[:top]
    return [w for w in ranked
            if w not in deck and not lemmas_of.get(w, set()) & deck]


def frequency_report():
    if not (FREQ_PATH.exists() and DICT_PATH.exists()):
        print("no data/raw sources - run tools/fetch_sources.py")
        return
    words = json.loads((ROOT / "data" / "words.json")
                       .read_text(encoding="utf-8"))["words"]
    main = {w["sq"] for w in words if not w.get("extended")}
    every = {w["sq"] for w in words}
    count = frequency_counts()
    lemmas_of = lemma_index()
    print("coverage of the frequency list (%s)" % FREQ_PATH.name)
    print("  %-34s %10s %14s" % ("", "exact form", "form or lemma"))
    for name, deck in (("main course (%d cards)" % len(main), main),
                       ("whole course (%d cards)" % len(every), every)):
        print("  %-34s %9.1f%% %13.1f%%"
              % (name, 100 * coverage(deck, count),
                 100 * coverage(deck, count, lemmas_of)))
    gap = uncovered_forms(main, count, lemmas_of)
    print("  top-1,411 forms the main course does not cover: %d" % len(gap))
    print("  most frequent: %s" % ", ".join(gap[:30]))


def main():
    frequency_report()
    print()

    corpus_dir = ROOT / "src_raw" / "opus"
    files = sorted(corpus_dir.glob("*.txt")) if corpus_dir.exists() else []
    if not files:
        print("no corpora in %s - run tools/corpus/fetch_more.py" % corpus_dir)
        return 0

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
