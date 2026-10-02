#!/usr/bin/env python3
"""Select learner-appropriate example sentences for course cards from OPUS corpora.

Design constraints, in priority order:
  1. The sentence must actually USE the target word in its intended sense.
     This is the bug class that kept biting: a card glossed "and" illustrated
     with a sentence where the word was functioning as something else.
  2. Prefer sentences built only from vocabulary the learner has already met
     (same level or earlier).
  3. Prefer short sentences.
  4. Only human-translated parallel corpora are trusted. Machine-translated
     output teaches wrong sentences, and we cannot detect that automatically.

Wiktionary examples already present in the deck are authoritative and are not
replaced; this tool only fills gaps.
"""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

# ROOT is the repo root. These paths used to carry a spurious 'albcourse/'
# segment, which resolved to a directory that does not exist, so the deck
# loaded as zero words and the run divided by zero. It failed loudly only at
# the coverage print; the real symptom was that nothing was ever selected.
# ROOT is the REPO root. This file is tools/corpus/select_examples.py, so three
# parents up is the repo, not two (which lands on tools/ and made every data
# path below miss by a directory).
ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS_DIR = ROOT / "src_raw" / "opus"
WORDS_JSON = ROOT / "data" / "words.json"
LEVEL_DIR = ROOT / "data" / "levels"

# Human-translated only. WikiMatrix / wikimedia / Tanzil are MT-derived and are
# deliberately excluded: a wrong sentence is worse than a missing one.
# Human-translated only, in descending priority. WikiMatrix / wikimedia /
# Tanzil are MT-derived and are deliberately excluded: a wrong sentence is
# worse than a missing one.
#
# HPLT is the wiki translation corpus and is by far the largest (6.8M pairs);
# it is what closed the last 160 missing words. MaCoCu is professionally
# translated film/TV subtitles, bible-uedin is scripture. All three were added
# after the first pass left 1,270 cards without an example.
HUMAN = ["Tatoeba", "EUbookshop", "TildeMODEL", "GlobalVoices",
         "TED2020", "QED", "GNOME", "SETIMES",
         "MaCoCu", "bible-uedin", "HPLT",
         "ELRC-3052-wikipedia_health"]

TOKEN_RE = re.compile(r"[a-zA-Z\u00eb\u00cb\u00e7\u00c7]+")
MIN_WORDS, MAX_WORDS = 3, 9

# Candidates retained per distinct token. The selector ranks on sense, level and
# length, so a handful is enough and this bounds memory on very large corpora.
MAX_CANDIDATES_PER_TOKEN = 400

# Words whose surface form is ambiguous, so the English side must corroborate
# the sense we are illustrating. Maps deck word -> required regex in the English.
SENSE_GUARD = {
    "e": r"\band\b",
    "dhe": r"\band\b",
    "por": r"\bbut\b",
    "ose": r"\bor\b",
    "sepse": r"\bbecause\b",
    "ndërsa": r"\bwhile\b",
    "që": r"\bthat\b",
    "se": r"\bif\b|\bthat\b|\bwhether\b",
    "me": r"\bwith\b|\bby\b",
    "pa": r"\bwithout\b",
    "prej": r"\bfrom\b",
    "tek": r"\bto\b|\bat\b",
    "mbi": r"\bon\b|\bover\b|\babout\b",
    "nën": r"\bunder\b|\bbeneath\b",
    "ndërmjet": r"\bbetween\b|\bamong\b",
    "rreth": r"\babout\b|\baround\b",
    "pas": r"\bafter\b|\bbehind\b",
    "para": r"\bbefore\b|\bin\s+front\b",
    "deri": r"\buntil\b|\bto\b",
    "sipas": r"\baccording\b",
    "gjatë": r"\bduring\b",
    "kundër": r"\bagainst\b|\bagainst\b",
    "përveç": r"\bexcept\b|\bapart\b",
    "midis": r"\bamid\b|\bbetween\b",
}

# Transcript corpora (TED, SETIMES, QED) carry speaker labels, fragments and
# trailing ellipses. Those fragments are not reference sentences, and teaching
# them would be worse than showing nothing. Every one of these is a case that a
# naive length filter lets through, e.g. "Dhe une ...." for the word "dhe".
SPEAKER = re.compile(r"^\s*[A-Z][A-Za-z]{0,12}:\s*")
DASH = re.compile(r"^[-–—]\s*")
TRAIL = re.compile(r"\s*\.{2,}.*$")
EN_META = re.compile(
    r'[\u201c\u201d]|\.{2,}|\?{2,}|^[-–—]|:$|\(|\)|\bLM\b|\bDr\b|\bMr\b|\bApplause\b')
SQ_META = re.compile(r'\.{2,}|\?{2,}|--|^\s*[-–—]\s|^["\u201c]')
PAREN = re.compile(r"\(|\)|%|https?://|\bwww\.")

# A complete sentence ends in terminal punctuation on BOTH sides. Transcript
# corpora are full of mid-sentence fragments that look short and cheap but
# teach nothing. Requiring punctuation roughly halves the pool and removes
# every fragment found in the function-word audit.
TERMINAL = re.compile('[.!?][' + chr(34) + chr(39) + chr(0x201d) + ']?$')
QUOTE_ANY = re.compile('[' + chr(34) + chr(0x201c) + chr(0x201d) + ']')
DASHGAP = re.compile('--| - ')

# HPLT is a wiki corpus and carries file paths, shell fragments, product
# codes and bare dates. They survive every language gate while teaching
# nothing: 'cpuinfo-fil' was offered for the word 'fil'.
TECH = re.compile(r"/ ?proc ?/|/ ?dev ?/|/ ?usr ?/|/ ?etc ?/|/ ?var ?/|https?://|www\.|[A-Za-z]:\\\\|\w+\-\w+\\|\w+\.\w[a-z]{2,4}\b|/\w+\/|\d{2,}|CPU|MDR|SEBI|EPR|STEM|CTE|NICE|\b[A-Z]{2,}\b|\[\d{1,3}\]")
# The user requires no acronyms or shouty capitals in any example. Albanian
# orthography has no internal capitals, so a mid-sentence run of 2+ capitals is
# jargon ('HTML5', 'DHUNEE', 'TRANSPLANTIMI'). Sentences written entirely in
# capitals are shouting and are rejected too.
ACRONYM = re.compile("(?<![.!?] )(?<![A-Za-z])[A-Z]{2,}")
SHOUT = re.compile("[^a-z]{6,}")

# HPLT is a wiki corpus, so it carries list bullets, bold/table markup and
# format placeholders. Those are not reference sentences: 'Cilesi e larte.'
# with a leading bullet, 'Gabim kur {0}.', and four exclamation marks.
WIKI_JUNK = re.compile("{[^}]*}|[\\/]s*|\d/\d|!{2,}|\?{2,}|[\u2022\u25cf\u2605\u25a0\u25aa]|\*\*|::|\|\s")

# Some transcript rows are not translated at all: the English column repeats
# the Albanian, sometimes with stray Cyrillic. We saw 'Unл nuk shkoj.' in the
# audit, whose English side was identical to the Albanian. A pair that is not
# a translation carries no gloss for the learner, so reject it outright.
CYRILLIC = re.compile('[Ѐ-ӿ]')
ALBANIAN_LETTERS = re.compile('[ëËçÇ]')
# (removed: a crude common-word test cost ~17k valid sentences for ~1k junk rows)


def iter_pairs():
    """Yield (corpus, en, sq) over every human corpus, streaming.

    HPLT alone is 1.8 GB / 6.8M pairs, so the corpora are read line by line and
    never held in memory. The quality gates run first, so at most a fraction of
    the pairs are ever indexed.
    """
    for name in HUMAN:
        path = CORPUS_DIR / (name + ".txt")
        if not path.exists():
            print("WARN missing corpus: " + name, file=sys.stderr)
            continue
        n = 0
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "\t" not in line:
                    continue
                en, sq = line.split("\t", 1)
                en, sq = en.strip(), sq.strip()
                if en and sq:
                    n += 1
                    if sentence_ok(en, sq) and alignment_ok(en, sq):
                        yield name, en, sq
        print("  %-32s %9d pairs scanned" % (name, n))


def clean_en(text):
    """Strip speaker labels, dashes and trailing ellipses from transcript English."""
    text = SPEAKER.sub("", text)
    text = DASH.sub("", text)
    text = TRAIL.sub("", text)
    return text.strip()


def sentence_ok(en, sq):
    n = len(sq.split())
    if n < MIN_WORDS or n > MAX_WORDS:
        return False
    en = clean_en(en)
    if EN_META.search(en) or SQ_META.search(sq):
        return False
    if PAREN.search(en) or PAREN.search(sq):
        return False
    if len(en) < 8:
        return False
    if not re.search(r"[a-zA-Z]", en) or not re.search(r"[a-zA-ZëËçÇ]", sq):
        return False
    if not TERMINAL.search(sq):
        return False
    if not TERMINAL.search(en):
        return False
    if QUOTE_ANY.search(sq) or QUOTE_ANY.search(en):
        return False
    if DASHGAP.search(sq) or DASHGAP.search(en):
        return False
    if TECH.search(sq) or TECH.search(en):
        return False
    if ACRONYM.search(sq) or ACRONYM.search(en):
        return False
    if SHOUT.search(sq) or SHOUT.search(en):
        return False
    if WIKI_JUNK.search(sq) or WIKI_JUNK.search(en):
        return False
    if CYRILLIC.search(en) or CYRILLIC.search(sq):
        return False
    if en.strip().lower() == sq.strip().lower():
        return False
    # Cheap alignment sanity: the two sides should be remotely comparable in bulk.
    ratio = len(en) / max(1, len(sq))
    if ratio < 0.25 or ratio > 4.0:
        return False
    return True


# Words whose Albanian usage varies by sense, where a sentence can be fluent and
# still not illustrate the gloss. 'e' is the clearest: in "një e tërë" it is the
# ARTICLE, yet the English carries an "and" from the sentence's first word
# ("Dhe kështu" = "And so"), so the English-side guard alone passes it. A card
# glossed "and" then shows a sentence with no conjunction in it, which is the
# defect this whole gate exists to prevent.
#
# The rule: for these words, require the SENSE MARKER to appear in the
# Albanian too, and forbid the known misleading senses.
SENSE_MARKER_SQ = {
    # A conjunction 'e' is simply a standalone token; the misleading senses
    # (article in 'një e tërë', preposition in 'e shtëpisë') are removed by
    # SENSE_FORBID_SQ instead, which is a far more precise tool than trying to
    # pattern-match every legitimate joining position.
    "e": r"(?<![a-zA-ZëëçÇ])\be(?![a-zA-ZëëçÇ])",
}

# Usage that the gloss does NOT mean, so the sentence is rejected outright.
SENSE_FORBID_SQ = {
    # ONLY the article sense: 'një e tërë' = a whole, where 'e' sits between a
    # numeral and the noun it governs. A broader "e + word" rule was tried and
    # rejected: it also killed genuine conjunctions such as 'dhe e quajti' and
    # 'tridhjetë e katër vjet', which are exactly the sentences we want.
    "e": r"\bnjë\s+e\s+[a-zëç]+",
}


def context_ok(sq, sq_word, pos_index):
    """Decide whether every occurrence of sq_word in sq is provably the glossed sense.

    The English-side SENSE_GUARD validates the WHOLE sentence: for 'e' the rule
    is /\\band\\b/, so a sentence whose 'and' comes from an unrelated 'dhe'
    passes even though the 'e' is the article. That is the shipped defect
    ('...dhe eshte shume e lire.').

    Three REJECTION rules were tried and all three were falsified, because each
    killed genuine conjunctions ('me e madhe', 'Bordet e rregullta', 'dhe e
    quajti'). So this does the opposite: it ACCEPTS only contexts that prove
    the intended sense, using the deck's own part-of-speech data rather than a
    hand-written pattern. A sentence it is unsure about is simply not chosen,
    which costs an example but never teaches the wrong one.

    A joining 'e'/'dhe' sits before a VERB or a PRONOUN ('e dua', 'e cila'), or
    between two NUMERALS in a compound ('tridhjetë e katër vjet'). An article
    'e' sits before a NOUN or ADJECTIVE ('e lirë', 'e qytetit'). The two are
    told apart by the following token's POS.
    """
    toks = TOKEN_RE.findall(sq.lower())
    target = sq_word.lower()
    seen = False

    def pos_of(tok):
        return (pos_index.get(tok) or [])

    PROBES = (("verb", "verb"), ("pron", "pron"), ("num", "num"),
              ("noun", "noun"), ("adj", "adj"))

    def kinds(tok):
        """Every part-of-speech class the deck's own labels support for tok."""
        ps = pos_of(tok)
        return {tag for probe, tag in PROBES if any(probe in p for p in ps)}

    # Particles and auxiliaries can stand between a joining 'e' and its verb
    # ('e të shërbej', 'e nuk do të vdisni'). These are function words, never
    # the noun an article 'e' would govern, so the scan looks through them.
    # Article readings ('e lirë', 'e qytetit') are still rejected because the
    # token right after the joiner is a noun or adjective there.
    FUNCTION = {"të", "te", "t", "nuk", "do", "jo", "po", "se", "qe"}

    def is_function(tok):
        if tok in FUNCTION:
            return True
        labs = pos_of(tok)
        # An adverb/particle/conjunction label on the next token also cannot be
        # the noun an article 'e' governs.
        return any(("adv" in lab) or ("part" in lab) or ("conj" in lab) for lab in labs)

    for i, tok in enumerate(toks):
        if tok != target:
            continue
        seen = True
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        prev = toks[i - 1] if i else None
        if not nxt:
            return False
        j = i + 1
        skipped = False
        while is_function(nxt) and j + 1 < len(toks):
            j += 1
            nxt = toks[j]
            skipped = True
        ks = kinds(nxt)
        kp = kinds(prev) if prev else set()
        # A noun reading on the following token means the ARTICLE sense, so a
        # token that could be either is rejected. 're' is labelled
        # ['noun','verb']; 'e re' in 'një eksperiencë e re dhe sfiduese' is
        # really conjunctive, but nothing local settles it, and the deck's own
        # rule is that a wrong example is worse than a missing one.
        if ks & {"noun", "adj"}:
            return False
        if ks & {"verb", "pron"}:
            continue
        if "num" in ks and "num" in kp:
            continue
        # An out-of-deck head ('vdisni', 'tere') proves nothing by itself, so
        # decide by position: after a skipped function word we are inside a
        # verb phrase ('e nuk do të vdisni'), which no article reading yields.
        # Directly after the joiner nothing is provable ('një e tere'), so
        # refuse instead of guessing.
        if not ks and skipped:
            continue
        return False
    return seen


def article_reading(sq, sq_word, pos_index):
    """True if sq_word is used as the definite ARTICLE in this sentence.

    The article's signature is a following NOUN or ADJECTIVE ('e qytetit',
    'e lirë'), which is what separates it from a joining 'e' ('e dua').
    Note the adjective case: the original defect '...shume e lire.' is an
    article governing an ADJECTIVE, so a noun-only test misses the exact
    sentence this whole gate exists to catch.

    Kept separate from context_ok() on purpose: context_ok() is conservative and
    returns False whenever it cannot PROVE the conjunction, which is a
    different question from positively identifying the article. Reporting the
    two separately is what lets the verifier say which sense it saw.
    """
    toks = TOKEN_RE.findall(sq.lower())
    target = sq_word.lower()
    for i, tok in enumerate(toks):
        if tok != target or i + 1 >= len(toks):
            continue
        labs = pos_index.get(toks[i + 1]) or []
        if any(("noun" in (l or "")) or ("adj" in (l or "")) for l in labs):
            return True
    return False


def alignment_ok(en, sq):
    """Reject known misalignments using symmetric conjunction markers."""
    e, s = en.lower(), sq.lower()
    if re.search(r"\band\b", e):
        if " dhe " not in s and " e " not in s and not s.startswith("dhe ") and not s.startswith("e "):
            return False
    if re.search(r"\bor\b", e) and " ose " not in s:
        return False
    return True


def main():
    # Read the LEVEL files, not data/words.json. The flat index has corpus
    # examples merged into it by build_words_index.py, so using it here made
    # the selector treat its own previous output as "already done" and skip
    # 2,078 words. The level files carry only the dictionary's own examples.
    deck_words = []
    for lv in sorted(LEVEL_DIR.glob("level_*.json")):
        payload = json.loads(lv.read_text(encoding="utf-8"))
        for w in payload["words"]:
            # Mirror build_words_index.pick_example exactly. It used to count
            # ANY sense's example, so a word whose headline sense has none but
            # a sibling POS does (mirë "good" vs the adverb "well") was treated
            # as already done and never targeted, and then shipped with no
            # sentence at all. The two components must agree on this.
            ex = None
            senses = w.get("sense_detail") or []
            if senses:
                home = senses[0]
                home_pos = home.get("pos")

                def usable(sense):
                    return [e2 for e2 in (sense.get("examples") or [])
                            if isinstance(e2, dict) and e2.get("sq") and e2.get("en")]

                if usable(home):
                    ex = {"sq": usable(home)[0]["sq"], "en": usable(home)[0]["en"]}
                else:
                    for sense in senses[1:]:
                        if sense.get("pos") != home_pos:
                            continue
                        same = usable(sense)
                        if same:
                            ex = {"sq": same[0]["sq"], "en": same[0]["en"]}
                            break
            deck_words.append({
                "sq": w["sq"],
                "level": w.get("level") or payload.get("level"),
                "wiktionary_example": ex,
                # Needed by context_ok() to tell a joining 'e' from the
                # article 'e' by the POS of the token that follows it.
                "pos": [str(p).lower() for p in (w.get("pos") or [])],
            })

    # Fail here, not at the coverage print. An empty deck once ran to the end
    # and only surfaced as a ZeroDivisionError, which reads like a maths slip
    # rather than a wrong path.
    if not deck_words:
        print("FATAL: no level files found under %s" % LEVEL_DIR, file=sys.stderr)
        return 1

    word_level = {w["sq"]: w["level"] for w in deck_words}
    deck_set = set(word_level)
    # POS lookup for context_ok(). The deck's own labels, so the gate agrees
    # with what the card actually claims rather than a hand-written guess.
    pos_index = {}
    for w in deck_words:
        for lab in w.get("pos") or []:
            pos_index.setdefault(w["sq"].lower(), [])
            if lab not in pos_index[w["sq"].lower()]:
                pos_index[w["sq"].lower()].append(lab)
    have_example = {w["sq"] for w in deck_words if w.get("wiktionary_example")}

    # Index: token -> list of (corpus, en, sq). Only gated pairs are kept, and
    # for a given token only the best few are worth holding: the selector only
    # ever needs the top candidate, and an unbounded list would be 6.8M pairs
    # of memory for HPLT alone.
    # Per-token reservoir, so a word that only appears late (or only in the
    # last corpus read) is not crowded out by common words seen earlier.
    # seen[tok] counts occurrences; we keep MAX_CANDIDATES_PER_TOKEN of them,
    # replacing a random existing entry with probability
    # MAX / (seen + 1), which is textbook reservoir sampling.
    index = {}
    seen = {}
    rng = random.Random(20260929)
    kept = 0
    for name, en, sq in iter_pairs():
        kept += 1
        for tok in set(TOKEN_RE.findall(sq.lower())):
            n = seen.get(tok, 0) + 1
            seen[tok] = n
            bucket = index.setdefault(tok, [])
            if len(bucket) < MAX_CANDIDATES_PER_TOKEN:
                bucket.append((name, en, sq))
            else:
                j = rng.randrange(n)
                if j < MAX_CANDIDATES_PER_TOKEN:
                    bucket[j] = (name, en, sq)
    print("after quality gates:", kept)

    targets = [w for w in deck_words if w["sq"] not in have_example]
    print("cards needing an example:", len(targets))

    results = {}
    rejected = {"no_candidate": 0, "guard": 0}
    for w in targets:
        sq_word = w["sq"]
        level = w["level"]
        cands = index.get(sq_word.lower(), [])
        guard = SENSE_GUARD.get(sq_word)
        best = None
        best_key = None
        for name, en, sq in cands:
            if guard and not re.search(guard, clean_en(en), re.I):
                continue
            toks = TOKEN_RE.findall(sq.lower())
            # Own token only: 'fil' must not match inside 'cpuinfo-fil'.
            if sq_word.lower() not in toks:
                continue
            # Reject sentences where the word is present but used in a sense
            # the gloss does not name (e.g. the article 'e' in 'një e tërë').
            forbid = SENSE_FORBID_SQ.get(sq_word)
            if forbid and re.search(forbid, sq.lower()):
                continue
            # Provable-context check. Rejects sentences where the token sits in
            # a context that reads as a different part of speech than the gloss
            # claims (the article 'e' in '... eshte shume e lire.'). Applied to
            # guarded, sense-ambiguous words only; an unprovable sentence simply
            # loses the example rather than teaching the wrong sense.
            if sq_word in SENSE_GUARD and not context_ok(sq, sq_word, pos_index):
                continue
            marker = SENSE_MARKER_SQ.get(sq_word)
            if marker and not re.search(marker, sq.lower()):
                continue
            known = 0
            unknown = 0
            for t in toks:
                lv = word_level.get(t)
                if lv is not None and lv <= level:
                    known += 1
                else:
                    unknown += 1
            # Prefer: all-vocabulary-known, then short, then higher-priority corpus.
            key = (unknown, len(toks), -known, HUMAN.index(name))
            if best_key is None or key < best_key:
                best_key = key
                best = (name, en, sq)
        if best is None:
            if cands:
                rejected["guard"] += 1
            else:
                rejected["no_candidate"] += 1
            continue
        results[sq_word] = {
            "sq": best[2],
            "en": clean_en(best[1]),
            "corpus": best[0],
            "score": list(best_key),
        }

    print()
    print("filled:", len(results), "of", len(targets))
    print("  no candidate at all :", rejected["no_candidate"])
    print("  only sense-guard fail:", rejected["guard"])
    total_after = len(have_example) + len(results)
    print("deck coverage: %d / %d = %.1f%%" % (total_after, len(deck_words), 100.0 * total_after / len(deck_words)))

    by_corpus = {}
    for v in results.values():
        by_corpus[v["corpus"]] = by_corpus.get(v["corpus"], 0) + 1
    print()
    print("chosen corpus mix:")
    for k in sorted(by_corpus, key=lambda x: -by_corpus[x]):
        print("  %-14s %d" % (k, by_corpus[k]))

    # data/, not the repo root. build_words_index.CORPUS_EXAMPLES reads
    # data/corpus_examples.json, so writing anywhere else produced a file the
    # build never read: re-running selection changed nothing in the deck and
    # the stale examples persisted. Same failure shape as the earlier ROOT
    # bug that made the deck load as zero words.
    out = ROOT / "data" / "corpus_examples.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True))
    print()
    print("wrote " + str(out.relative_to(ROOT)))


if __name__ == "__main__":
    sys.exit(main() or 0)
