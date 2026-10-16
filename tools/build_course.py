#!/usr/bin/env python3
"""
build_course.py - build the albcourse SRS dataset from real source data.

Inputs (unpacked from data/sources/ by tools/fetch_sources.py):
  data/raw/kaikki_albanian.jsonl   Kaikki.org / wiktextract of English Wiktionary
  data/raw/sq_50k.txt              hermitdave FrequencyWords, OpenSubtitles2018

Outputs:
  data/course.json          course manifest
  data/index.json           per-level summary for the level picker
  data/levels/level_NN.json  one file per level (the web app lazy-loads these)
  data/report.json          build statistics + coverage warnings

Design rules:
  * Nothing is invented. Every word, gloss, POS and etymology is extracted
    from the two sources above. There are no hand-written entries.
  * A word only enters the deck if it occurs in the frequency list, so learners
    only meet words that actually appear in real Albanian text.
  * Inflections and spelling variants are NOT vocabulary. They are filtered with
    Wiktionary's structured sense tags (form-of / alt-of), never by pattern
    matching the English gloss text.
  * A word that is several parts of speech at once ('e', 'të', 'ka') becomes ONE
    card listing all its senses, because that is how it actually behaves in a
    sentence. Duplicate ids would break spaced repetition state.
  * Albanian 'e-diaeresis' and 'c-cedilla' are alphabet letters, not diacritics,
    so they are never stripped: 'te' and 'të' are different words.
"""

import json
import added_words
import form_gloss
import form_senses
import gloss_overrides
import orthography
import teaching_order
import pack_shape
import pos_balance
import opening_levels
import opening_policy
import cognates
import affixes
from example_rank import rank_examples
import os
import re
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data")
LEVELS_DIR = os.path.join(OUT, "levels")

# Reference sentences mined from human-translated parallel corpora (OPUS).
# Wiktionary examples always win: authored for the headword and tied to the
# exact sense. This only fills cards that have none, and every sentence was
# checked to render the intended sense. Kept in the level files as well as
# the flat index so the lesson view and the review card agree.
CORPUS_EXAMPLES_PATH = os.path.join(OUT, "corpus_examples.json")

# Parts of speech that carry learnable vocabulary.
# Excluded: 'name' (proper nouns), 'character' (single letters),
# 'suffix'/'prefix'/'infix' (bound morphemes), 'particle' and 'symbol'.
CORE_POS = {"noun", "verb", "adj", "adv", "pron", "num", "intj", "prep", "conj", "det"}

# Frequency ceiling for admitting a card for an inflected form. The deck is
# built to be a Joyo-shaped course of common vocabulary, so a form is added
# only where a learner actually meets the inflected word rather than the
# lemma. Measured with tools/measure_form_gap.py: rank <= 2000 admits 183
# cards and covers every one of the 116 forms inside the top 500, while
# rank <= 5000 would add 669 and pull in rare conjugations nobody meets yet.
FORM_CARD_MAX_RANK = 2000

# How common a family member must be to compete for a slot in the opening
# levels. See "the opening must not be crowded out by a family's rare tail"
# in assign_levels().
OPENING_MEMBER_MAX_RANK = 1200

# Roots named in a multi-root level's title before the "+N" tail.
TITLE_ROOTS = 3

# How many rare members a family must have before deferring them is worth an
# extra session.
#
# Deferring is not free: a deferred family's tail takes a level of its own.
# Measured, 103 families had exactly ONE rare member -- lexim beside lexoj,
# and dozens like it -- and deferring those cost 103 extra sessions, which
# pushed the course past its 800-level ceiling. One stray rare member crowds
# nothing out, so outside the opening only a genuinely large tail is split.
# Families that compete for the opening shed any tail at all (see
# assign_levels(), "root first, tail later").
OPENING_MIN_DEFERRED = 4

# The main course teaches the words ranked up to here; the rest is an
# optional extended track that follows it (RECOMMENDATIONS.md section 3.6).
# Measured on the pinned sources: 340 levels reach 80.9% of tokens counted
# by form or lemma, against 83.8% for all 801 levels. The curated opening
# and the stems of main-course words are main course whatever their rank.
MAIN_MAX_RANK = 5000

# Closed-class roots deferred past the opening get a synthetic rank just
# beyond this one, so they are taught after the opening rather than dropped.
DEFER_MAX_ROOT_RANK = 900
# ...and are then spread through the course rather than stacked there: the
# first after this many scheduled families (two levels' worth, so the
# scheduler's first levels stay content words), then one every
# DEFER_SPREAD_EVERY families, about one per level.
DEFER_SPREAD_AFTER = 10
DEFER_SPREAD_EVERY = 4

# Order in which a multi-POS word should be presented.
#
# Closed-class words (conjunction, preposition, pronoun, adverb, determiner)
# come first: if a word is both a noun and a conjunction, the learner almost
# always meets the function-word sense in real text. This is what puts
# 'e' -> "and" (not the accusative clitic) and 'unë' -> "I" (not "potsherd").
# Content words keep the usual noun/verb/adjective order among themselves.
POS_ORDER = ["conj", "prep", "pron", "adv", "det", "num", "intj", "noun", "verb", "adj"]

# Senses whose POS alone determines the most useful headline. These are put
# ahead of every content-word sense; everything else keeps Wiktionary's own
# file order. See sort_senses in load_dict.
FUNC_POS = ["conj", "prep", "pron", "det", "num", "intj"]

# Kaikki tags a sense with a grammatical gender when it belongs to a homograph
# that needs disambiguating. A gender-tagged noun is usually that rare
# homograph, so it loses its headline slot when the word also carries an
# untagged verb or adverb. See sort_senses in load_dict.
GENDER_TAGS = {"masculine", "feminine", "neuter"}
POS_LABEL = {
    "noun": "noun", "verb": "verb", "adj": "adjective", "adv": "adverb",
    "pron": "pronoun", "prep": "preposition", "conj": "conjunction",
    "det": "determiner", "num": "numeral", "intj": "interjection",
    "particle": "particle",
}

ETY_CLASS = {
    "inh": "inherited", "der": "derived", "bor": "borrowed",
    "bor+": "borrowed", "compound": "compound", "af": "affix",
    "suffix": "affix", "prefix": "affix", "affix": "affix", "root": "root",
}

# 'From <Language>' in etymology_text -> short code, for the source-language badge.
SOURCE_LANGS = {
    "Latin": "la", "Ottoman": "tr", "Greek": "el", "Ancient": "el",
    "Italian": "it", "French": "fr", "Arabic": "ar", "Turkish": "tr",
    "Serbo": "sr", "South": "sr", "German": "de", "English": "en",
    "Russian": "ru", "Spanish": "es", "Slav": "ru", "Vulgar": "la",
    "Late": "la", "New": "it",
}

# Albanian alphabet letters, plus the two letters unique to Albanian.
LATIN_LETTERS = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                 "ëçËÇ")
_LET = re.escape(LATIN_LETTERS)
ALPHABET_RE = re.compile("^[" + _LET + "]+$")
PARENT_RE = re.compile(
    r"(?:From|of|borrowed from|diminutive of|augmentative of)\s+"
    "([" + _LET + "]{2,})\b")
QUOTED_RE = re.compile("[“\"'‘]([" + _LET + "]{2,})"
                       "[”\"'’]")
FROM_LANG_RE = re.compile(r"\bFrom\s+([A-Z][A-Za-z]+)")

# A gloss longer than this is a sentence, not a definition; use it as extra
# context rather than as the headline definition.
LONG_GLOSS = 90


# ----------------------------------------------------------------- frequency

def load_freq(path):
    """word -> (rank, count). Rank is 1-based; lower is more common.

    No accent folding: in Albanian 'e-with-diaeresis' is a distinct alphabet
    letter, so 'te' and 'te-diaeresis' are different words.
    """
    freq = {}
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.rsplit(" ", 1)
            if len(parts) != 2:
                continue
            w, c = parts[0], parts[1]
            try:
                c = int(c)
            except ValueError:
                continue
            if w not in freq or c > freq[w][1]:
                freq[w] = (i + 1, c)
    return freq


# ------------------------------------------------------------------ senses

def sense_is_content(sense):
    """True if this sense defines the word, rather than pointing at another one.

    Uses Wiktionary's structured tags: an inflected form or a spelling variant
    carries a form_of/alt_of link plus a form-of/alt-of tag. Those are already
    covered by the lemma's own inflection table, so they are not vocabulary.
    """
    tags = set(sense.get("tags") or [])
    if "form-of" in tags or "alt-of" in tags:
        return False
    if sense.get("form_of") or sense.get("alt_of"):
        return False
    return True


def form_lemma_of(card):
    """The lemma a form card points at, or None for an ordinary card."""
    for s in card.get("senses") or []:
        if s.get("is_form_of"):
            return s["is_form_of"]
    return None


def add_form_cards(cards, path, freq, max_rank):
    """Add cards for frequent inflected forms, filed under their lemma.

    Returns the list of added words. A form is admitted only when the word has
    no content sense of its own, is within the frequency cut, and its gloss
    names a real grammatical slot and a lemma the deck already teaches. That
    yields 183 cards at rank <= 2000, dominated by the copula and the auxiliaries
    a learner meets in the very first sentences ('eshte' rank 6, 'jane' rank
    54) rather than in a dictionary's inflection table.
    """
    known = {c["word"] for c in cards}
    added = []
    for j in read_entries(path):
        if j.get("lang_code") != "sq":
            continue
        pos = j.get("pos")
        if pos not in CORE_POS:
            continue
        w = (j.get("word") or "").strip()
        if not w or not ALPHABET_RE.match(w) or w in known:
            continue
        f = freq.get(w)
        if not f or f[0] > max_rank:
            continue
        s = form_sense_of(j, known)
        if s is None:
            continue
        gl = str((s.get("glosses") or [""])[0]).strip()
        lemma = form_senses.form_of_lemma(gl, s.get("tags"), words=known)
        if not lemma:
            continue
        rank, count = f
        ety = parse_etymology(j)
        cards.append({
            "word": w,
            "rank": rank,
            "count": count,
            # One sense only. The gloss is a grammatical description, so the
            # card is tagged as a form rather than presenting it as vocabulary
            # in its own right; the lemma link is what makes it learnable.
            "senses": [{
                "pos": pos,
                "pos_label": POS_LABEL.get(pos, pos),
                "gloss": gl,
                "tags": list(s.get("tags") or []),
                "cats": (s.get("categories") or [])[:3],
                "examples": [],
                "_src": 0,
                "is_form_of": lemma,
            }],
            "etymology": ety["text"],
            "etymology_class": ety["cls"],
            "parents": [],
            "source_lang": ety["source_lang"],
            "derived": [],
            "related": [],
            "forms": entry_forms(j),
        })
        known.add(w)
        added.append(w)
    return added


def read_entries(path):
    """Yield parsed Kaikki records, skipping unparseable lines."""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def content_senses(entry):
    return [s for s in (entry.get("senses") or []) if sense_is_content(s)]


def form_sense_of(entry, known_words):
    """The one form-of sense of 'entry' worth a card, or None.

    A form-of sense earns a card only when the word has no content sense of its
    own anywhere. Without that guard a minor sense of a word that is already a
    major entry wins on frequency: 'dhe' is the conjunction 'and' at rank 12 and
    the noun 'earth', and its aorist of 'jap' ('to give') would file it under a
    verb lemma and teach the wrong thing.

    form_senses.form_of_lemma decides which glosses qualify and returns the
    lemma they point at. The frequency gate is applied by the caller, not here,
    because the cut is a course decision rather than a property of the entry.
    """
    for s in entry.get("senses") or []:
        if sense_is_content(s):
            return None
        g = (s.get("glosses") or [None])[0]
        if not g:
            continue
        lemma = form_senses.form_of_lemma(g, s.get("tags"), words=known_words)
        if lemma:
            return s
    return None


def gloss_score(text, tags):
    """Prefer short, concrete, non-enumerated definitions as the headline."""
    n = len(text)
    score = 0
    # A short gloss is normal for function words ("and", "at", "I") and is a
    # strong signal of a real definition. The old -40 bonus was so large it
    # outranked sense order entirely, promoting "you" over "to, that" for
    # 'të'. A mild bonus keeps the preference without overriding POS order.
    if n <= 3:
        score -= 6
    if n > LONG_GLOSS:
        score += 30
    # 'masculine singular preposition, plural preposition' is parse noise
    if re.search(r"\b(masculine|feminine|neuter)\b.*\b(preposition|pronoun|noun)\b", text, re.I):
        score += 25
    if re.match(r"^(alternative form|obsolete form|standard form|misspelling)", text, re.I):
        score += 15
    if text.endswith("..."):
        score += 10
    # a definition that only names the POS adds nothing, e.g. 'a preposition'
    if re.fullmatch(r"(a|an|the)? ?[a-z]+ (preposition|pronoun|conjunction|adverb|noun|verb|article)", text.strip().lower()):
        score += 12
    # grammatical-gender boilerplate that Wiktionary puts in the gloss slot
    if re.search(r"\b(feminine|masculine|neuter)\b", text, re.I):
        score += 12
    # tag preferences: concrete, neutral, widely used
    if "Gheg" in tags or "dialectal" in tags or "Arvanitika" in tags:
        score += 12
    if "archaic" in tags or "obsolete" in tags or "rare" in tags:
        score += 10
    if "colloquial" in tags or "informal" in tags:
        score += 3
    if "figuratively" in tags:
        score += 2
    return score


# The orthography gate (see orthography.py). main() binds it once the
# dictionary and frequency list are loaded; None leaves examples ungated.
ORTHO = None
ORTHO_REJECTED = []


def extract_examples(sense, limit=2, headword=None, own_rank=10**9, freq=None):
    """Flatten a Kaikki sense's example dicts into small JSON-safe objects.

    Kaikki examples carry bilingual pairs plus Wiktionary bookkeeping fields
    (bold_*_offsets, ref, roman, tags). Only the human-readable fields are
    kept so the shipped JSON stays small and the app can render a sentence
    pair directly.
    """
    out = []
    for e in (sense.get("examples") or []):
        if not isinstance(e, dict):
            continue
        text = (e.get("text") or "").strip()
        if not text:
            continue
        if ORTHO is not None:
            bad = ORTHO.problems(text, headword)
            if bad:
                ORTHO_REJECTED.append(("wiktionary", headword, text, bad))
                continue
        tr = (e.get("translation") or e.get("english") or "").strip()
        out.append({
            "sq": text,
            "en": tr,
            # Where the headword sits in the Albanian sentence, so the app can
            # highlight it. Missing offsets simply mean no highlight.
            "offsets": e.get("bold_text_offsets") or [],
        })
        if len(out) >= 4:
            break
    # Rank before slicing: the learner asked for short sentences built
    # from vocabulary met at or before this word. See example_rank.py.
    return rank_examples(out, headword, own_rank, freq or {})[:limit]


def entry_senses(entry):
    """Content senses for one POS entry, best gloss first."""
    out = []
    for s in content_senses(entry):
        tags = s.get("tags") or []
        gl = (s.get("glosses") or [None])[0]
        if not gl:
            continue
        gl = str(gl).strip()
        if not gl:
            continue
        cats = s.get("categories") or []
        out.append({
            "gloss": gl,
            "tags": tags,
            "cats": cats,
            "score": gloss_score(gl, tags),
            "sense": s,
        })
    # Sort by score only. Python's sort is stable, so senses with equal scores
    # keep the order Wiktionary's editors chose, which puts the primary sense
    # first. Adding gloss length here would override that curation.
    out.sort(key=lambda d: d["score"])
    return out


# -------------------------------------------------------------- etymology

# --------------------------------------------------- derivation evidence

# Wiktionary's structured fields cannot be trusted as a derivation graph:
#
#   * "parents" is extracted from the etymology text by parse_etymology(), so
#     it picks up ENGLISH gloss words. nuk gets parents ["one", "not"],
#     where that "not" is the English word inside 'compare Latin non ("not")'.
#   * "derived" is a loose co-occurrence list. zbres ("descend") lists
#     falas/falem/fale/falje/faltore; bri ("rib") lists bori, an Ottoman loan
#     meaning "bugle".
#
# Both produced visible defects: nuk (the negator, "not, don't") was filed
# under not (the noun, "swim, swimming"), and bori under the inherited bri.
#
# So a family edge is accepted only when the ETYMOLOGY TEXT states a
# compositional derivation, which in Wiktionary's convention always has the
# form "<base> (“gloss”) + <affix>":
#
#     From marr + -es.          marr (take) + -em.        From gjithe + ca.
#     From ate (“father”) + dhe (“land”).
#
# The base is the last content token to the LEFT of the first "+", after
# stripping reconstruction stars, parentheticals and quoted glosses. Requiring
# a "+" is what separates derivation from mere mention: a cognate ("a cognate
# to Proto-Slavic *mora") or a comparison names no affix and yields no edge.
#
# Spelling similarity is not a substitute for this evidence: marre ("shame")
# and marrte ("twilight") are homographs of marr with unrelated meanings, and
# tmerr ("terror") is a cognate rather than a derivative.

_DERIV_LEAD_RE = re.compile(
    r"^\s*(?:from|of|compound\s+of|compound\s+formation\s+of|"
    r"derivation\s+from|continuing)\s+",
    re.IGNORECASE)
_DERIV_WORD_RE = re.compile(r"[\w\u00C0-\u024F'\u2019-]+", re.UNICODE)


# A comparison is not a derivation. nuk's etymology contains the aside
# "typologically compare Latin non (\"not\"), noenum (\"(Old Latin) idem\")
# (< ne + unus ~ unum)", where "ne + unus" describes LATIN, not Albanian. Scanning
# every sentence would otherwise link nuk to ne. The real derivations put
# the "+" in the sentence's main clause: esell reads "Interpretible as e- +
# sille", vdekje reads "vdes + -je".
_COMPARISON_RE = re.compile(
    r"\b(?:typologically\s+)?compare(?:d)?\b|\bcognates?\s+(?:with|include)\b|"
    r"\bcf\.\b|\bakin\s+to\b|\b(?:likewise|similarly)\b", re.IGNORECASE)

_PAREN_RE = re.compile(r"\([^)]*\)")


def _is_derivation_sentence(sent):
    """True if this sentence states a composition rather than comparing.

    Whether the equation may supply a BASE is decided in
    derivations_from_text(), which can see the affix itself; this only
    decides whether the sentence is about composition at all.
    """
    if _COMPARISON_RE.search(sent):
        return False
    # A "+" that lives entirely inside parentheses describes something else
    # (usually a foreign language); one in the main clause is the derivation.
    return "+" in _PAREN_RE.sub(" ", sent)


def derivations_from_text(text):
    """Base words this entry's etymology text says it is built FROM.

    Returns at most one base: a word's immediate ancestor is what makes it a
    family member, and a transitive chain is recovered by root_of() instead.
    """
    if not text:
        return []
    # Every sentence is scanned, not just the first. Wiktionary often states
    # the derivation after the reconstruction -- esell reads "...a privative e-
    # + sille. Interpretible as e- + sille" -- so a first-sentence-only rule
    # split genuine families apart (esell from its root e). Junk that survives
    # the wider scan is filtered by requiring the base to be a real deck word,
    # which is what build_families() already does.
    sentences = re.split(r"(?<=[.;])\s", text.strip())
    head = None
    for sent in sentences:
        if _is_derivation_sentence(sent):
            head = sent
            break
    if head is None:
        return []

    left = head.split("+")[0]
    # A starred affix reconstructs an ANCESTOR, so the equation describes some
    # other word, not this one. See _is_derivation_sentence().
    #
    # The test is on the affix itself, not the clause. esell reads "From
    # Proto-Albanian *atsilna or *aila-, a compound equivalent to a privative
    # e- + sille", where the stars sit in an earlier aside and the derivation
    # is the unstarred e- at the end; a bare star-anywhere test would throw
    # that real derivation away. ti reads "...ablative teje is from locative
    # *toi + -je", where the affix IS the reconstruction and must be dropped.
    #
    # So: the equation counts only when the token immediately before the "+"
    # is an unstarred word. That is the affix, and it is the token the base is
    # taken from below.
    if _affix_is_reconstruction(left):
        return []
    left = _DERIV_LEAD_RE.sub("", left)
    left = left.replace("*", "")            # proto-form reconstruction stars
    left = re.sub(r"\([^)]*\)", " ", left)       # (gloss) / (note)
    left = re.sub(r'“[^”]*”', " ", left)  # curly-quoted gloss
    left = re.sub(r'"[^"]*"', " ", left)  # straight-quoted gloss

    toks = _DERIV_WORD_RE.findall(left)
    if not toks:
        return []
    base = toks[-1].rstrip("-")             # "di- + si" -> di
    if not base:
        return []
    return [base]


# Function words that appear as a JOINER in a three-part compound, where
# they join two lexical elements rather than being a base. In a two-part
# equation the same word is a legitimate stem (në + se -> nëse).
_COMPOUND_JOINERS = {"e", "edhe", "dhe", "ose", "apo", "me"}


def _part_is_word(chunk, words):
    """True if this side of the equation names a real deck word."""
    w = _side_word(chunk, words)
    return bool(w) and w in words


_CLAUSE_BREAK = re.compile(r"[,;:\n]")


def _stem_side(chunk):
    """The stem side of a derivation equation, bounded to its own clause.

    A derivation is "base + affix", so the base sits in the text immediately
    after the "+". Reading further is how prose got mistaken for composition:
    kush reads "...Proto-Indo-European *kʷos + *sos, meaning 'who (is) this'",
    where the "+" joins two RECONSTRUCTED PIE forms. _side_word() then matched
    the spelling "sos" against the deck word sos ("indeed"), inventing an
    edge ai/kush -> sos and holding ai (rank 35) back to L614. The same
    happened to kurrë, mbi, tetë and rrafsh.

    So the stem side is cut at the first clause boundary -- the equation does
    not run past a comma -- and a side carrying a reconstruction marker (*)
    describes a reconstructed ancestor rather than a word the learner meets,
    so it yields no stem.

    This is deliberately narrow. It keeps every real composition, including
    the headline cases esëll = e- + sillë, shkruaj = sh- + kruaj and
    bashkëpunim = bashkëpunoj + -im, none of which has a clause break or a
    star between the "+" and its base.
    """
    side = _CLAUSE_BREAK.split(chunk)[0]
    if "*" in side:
        return ""
    return side


def _affix_is_reconstruction(left):
    """True if the LEFT of an equation is a starred reconstructed form.

    The affix is the last word before the "+". esell reads "...a privative e-
    + sille", where e- is unstarred and real, while ti reads "...from locative
    *toí + -je", where *toí reconstructs an ancestor. A bare test for "*"
    anywhere in the clause would reject esell too, because its sentence opens
    with the starred reconstruction "From Proto-Albanian *a-tšilna". So the
    star is only read when it is attached to the affix itself.

    "Attached" covers a reconstruction with an optional segment: tetë
    ("eight") reads "From *(a)te + -të", and *(a)te is not the preposition
    te. Matching only "*" + the last word missed it, so tetë was filed in
    the family of te ("at, to").
    """
    ctx = _DERIV_LEAD_RE.sub("", left)
    toks = _DERIV_WORD_RE.findall(ctx)
    if not toks:
        return False
    chunk = ctx.split()[-1] if ctx.split() else ""
    return chunk.startswith("*") and chunk.endswith(toks[-1])


def components_of(text, words):
    """The deck words this entry says it is built FROM, with their role.

    A derivation sentence is a two-sided equation -- "e- + sille", "ne + drite" --
    so both sides matter, and they are not the same kind of thing:

      * The LEFT side is the affix. This is what build_families() already
        follows, which is why esell groups under the family e.
      * The RIGHT side is the stem -- the lexical word the learner has to
        know first. sille ("breakfast") is the stem for esell, and it is a
        real deck word, so it is worth naming and teaching first.

    Both sides are required to be real deck words. That is what keeps the
    junk out: nuk gets parents ["one", "not"] from English glosses, and the
    Ottoman bori -> bri is a false association, because neither is a word
    the course teaches.

    Returns [(word, role), ...] in reading order, or []. Roles:
      prefix  pa- in pa- + fund (a deck word, or marked with a hyphen)
      stem    fund in pa- + fund; creates a prerequisite edge
      base    mund in mund + -ësi; displayed like a stem, no edge
      suffix  ësi in mund + -ësi (stored without the hyphen)
    """
    if not text:
        return []
    for sent in re.split(r"(?<=[.;])\s", text.strip()):
        if "+" not in sent or not _is_derivation_sentence(sent):
            continue

        sides = sent.split("+")
        pre = _side_word(sides[0])
        # The stem side is read against the deck, so a trailing description
        # ("dritë, a brightening of ndriç") cannot displace the real base.
        stem = _side_word(_stem_side(sides[1]), words) \
            if len(sides) >= 2 else None

        # A starred AFFIX means the equation reconstructs an ancestor, so it
        # describes some other word and yields no stem either. Without this,
        # ti ("you", rank 18) took meje as its stem: its etymology ends
        # "...ablative teje is from locative *toí + -je from meje", and reading
        # the text after the "+" found meje sitting in the prose. That gave
        # the second most common pronoun a prerequisite on a rank-423 word and
        # held it to L140. _stem_side() guards the right of the equation and
        # the affix guard guards the left, so a reconstruction now contributes
        # neither side.
        if _affix_is_reconstruction(sides[0]):
            stem = None

        # A short function word sitting BETWEEN two lexical elements is a
        # joiner, not a stem: gjëegjëzë is gjë + e + gjëzë, where e is
        # the conjunctive "and" and no base has to be learned first.
        # In a TWO-part equation the same word is a real stem, and a
        # useful one -- nëse is në + se, and knowing se first helps. So
        # the rule is deliberately narrow: three or more parts only.
        if stem and len(sides) >= 3 and stem in _COMPOUND_JOINERS:
            if _part_is_word(sides[-1], words) or _part_is_word(sides[1], words):
                stem = None

        # A SUFFIX equation reads the other way round: "mund + -ësi" puts the
        # base on the LEFT and the affix on the right. Reading the left side as
        # a prefix rendered mundësi as "from mund-" on 514 cards, and threw the
        # suffix away, so no card ever showed one. The left is a prefix only
        # when the text marks it with a hyphen ("pa- + fund"); an unmarked left
        # followed by a hyphen-led right side is the base word.
        #
        # Its role is "base", not "stem", on purpose. A stem creates a
        # prerequisite edge in assign_levels(); a suffix base never did (it
        # was filed as the family root, and build_families() already groups
        # the word under it). Promoting 456 bases to edges would re-order the
        # course -- pasur (L15) would wait for pasë (L551) -- which is a
        # scheduling decision (RECOMMENDATIONS.md 3.1), not a display fix.
        suffix = None
        if len(sides) >= 2 and _suffix_of(sides[1]):
            suffix = _suffix_of(sides[1])
            if not _left_is_prefix(sides[0]):
                base = pre if not _affix_is_reconstruction(sides[0]) else None
                out = []
                if base and base in words:
                    out.append((base, "base"))
                    out.append((suffix, "suffix"))
                return out
            stem = None
        elif len(sides) >= 3:
            suffix = _suffix_of(sides[-1])

        out = []
        # The affix is normally required to be a deck word too, and that filter
        # is load-bearing: dropping it lets prose into the component line
        # ("behind" for lashte, "appearance" for drite, Latin "communis" for
        # komunal -- 193 such tokens across the deck).
        #
        # Curated exclusions are the one deliberate exception
        # (pos_balance.EXCLUDE_WORDS, empty at present). The privative PREFIX
        # e- is the case this was written for: esell = e- + sille, egjell =
        # e- + gjell. It is shown on the component line as a label; it is not
        # the card e ("and"), and pos_balance.NOT_A_FAMILY_BASE keeps the
        # derivation from filing esell in that card's family.
        # It is a prefix, so per assign_levels it never creates a prerequisite
        # edge -- it is displayed, not re-ordered.
        #
        # A prefix the text itself marks with a hyphen ("zh- + vesh") is also
        # kept: the hyphen is the evidence the prose filter above lacks, and a
        # prefix never creates a prerequisite edge.
        # A bare one ("n-" on ndaj, with no stem in the deck) explains nothing,
        # so it is shown only beside a stem.
        has_stem = bool(stem and stem in words and stem != pre)
        if pre and (pre in words or pre in pos_balance.EXCLUDE_WORDS
                    or (has_stem and _left_is_prefix(sides[0])
                        and _AFFIX_RE.match(pre))):
            out.append((pre, "prefix"))
        if has_stem:
            out.append((stem, "stem"))
            if suffix:
                out.append((suffix, "suffix"))
        return out
    return []


# An affix is short and spelled in the Albanian alphabet. Anything else after
# a hyphen ("-Albanian", "-*kʷos") is prose, not a morpheme.
_AFFIX_RE = re.compile(r"^[a-zçë]{1,10}$")


def _clean_side(chunk):
    c = _DERIV_LEAD_RE.sub("", chunk)
    c = re.sub(r"\([^)]*\)", " ", c)
    c = re.sub(r'"[^"]*"', " ", c)
    c = re.sub(r"“[^”]*”", " ", c)
    return c


def _suffix_of(chunk):
    """The suffix a side of the equation opens with ("-ësi"), or None."""
    side = _CLAUSE_BREAK.split(chunk)[0]
    m = re.match(r"\s*-([^\W\d_]+)", _clean_side(side))
    if not m:
        return None
    suf = m.group(1).lower()
    return suf if _AFFIX_RE.match(suf) else None


def _left_is_prefix(chunk):
    """True if the text marks the left side as a prefix: "pa- + fund"."""
    toks = _DERIV_WORD_RE.findall(_clean_side(chunk).replace("*", ""))
    return bool(toks) and toks[-1].endswith("-") and len(toks[-1]) > 1


def _side_word(chunk, words=None):
    """The base word named by one side of a derivation equation.

    With no `words` set the LAST token wins, preserving the rule
    build_families() already relies on: the base is the final word before "+".

    With `words` supplied the FIRST real deck word wins instead, because a
    stem side usually runs into its own description -- "dritë, a brightening
    of ndriç" -- where the base is named first and the rest is commentary
    that must not be mistaken for it.
    """
    c = _DERIV_LEAD_RE.sub("", chunk)
    c = c.replace("*", "")                      # proto-form reconstruction stars
    c = re.sub(r"\([^)]*\)", " ", c)             # (gloss) / (note)
    c = re.sub(r'"[^"]*"', " ", c)             # straight-quoted gloss
    c = re.sub(r"“[^”]*”", " ", c)    # curly-quoted gloss
    toks = [t.rstrip("-") for t in _DERIV_WORD_RE.findall(c)]
    toks = [t for t in toks if t]
    if not toks:
        return None
    if words is not None:
        for t in toks:
            if t in words:
                return t
        return None
    return toks[-1]


def parse_etymology(entry):
    """text / cls / parents[] / source_lang, from a raw Kaikki entry."""
    text = (entry.get("etymology_text") or "").strip()
    cls = None
    for t in (entry.get("etymology_templates") or []):
        name = (t if isinstance(t, str) else str(t.get("name", ""))).strip()
        if name in ETY_CLASS:
            cls = ETY_CLASS[name]
            break

    parents = []
    if text:
        head = text.split(".")[0]
        for rx in (PARENT_RE, QUOTED_RE):
            for m in rx.finditer(head):
                w = m.group(1)
                if w not in parents:
                    parents.append(w)
            if parents:
                break

    src = None
    m = FROM_LANG_RE.search(text)
    if m and m.group(1) in SOURCE_LANGS:
        src = SOURCE_LANGS[m.group(1)]
    return {"text": text, "cls": cls, "parents": parents, "source_lang": src}


# ------------------------------------------------------------------ forms

def entry_forms(entry):
    """A few clearly-tagged inflections, for the word-detail panel."""
    out = {}
    for f in (entry.get("forms") or []):
        t = f.get("form")
        tags = f.get("tags") or []
        if not t or len(tags) != 1:
            continue
        if any(x in ("table-tags", "inflection-template") for x in tags):
            continue
        if not ALPHABET_RE.match(str(t)):
            continue
        out.setdefault(str(t), tags[0])
    return [{"form": k, "tag": v} for k, v in list(out.items())[:6]]


# ------------------------------------------------------------------- load

def load_dict(path, freq):
    """One card per surface word, with every content POS merged in."""
    cards = {}
    stats = Counter()

    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                j = json.loads(line)
            except Exception:
                stats["parse_error"] += 1
                continue
            if j.get("lang_code") != "sq":
                continue
            stats["sq_total"] += 1

            pos = j.get("pos")
            if pos == "particle" and j.get("word") in pos_balance.INCLUDE_PARTICLES:
                pass
            elif pos not in CORE_POS:
                stats["skipped_pos"] += 1
                continue
            w = (j.get("word") or "").strip()
            w = pos_balance.ARTICLED_ENTRIES.get(w, w)
            if not w or not ALPHABET_RE.match(w):
                stats["skipped_shape"] += 1
                continue
            # Curated exclusions. These are words the frequency list proves
            # are extremely common, so the frequency cut alone will never
            # remove them. "e" was the standing case until it was restored
            # with a reviewed gloss and example; see pos_balance.EXCLUDE_WORDS.
            if w in pos_balance.EXCLUDE_WORDS:
                stats["skipped_excluded"] += 1
                continue

            f = freq.get(w)
            if not f:
                stats["skipped_notfreq"] += 1
                continue

            senses = entry_senses(j)
            if not senses:
                stats["skipped_nogloss"] += 1
                continue
            rank, count = f
            ety = parse_etymology(j)

            card = cards.get(w)
            if card is None:
                card = cards[w] = {
                    "word": w,
                    "rank": rank,
                    "count": count,
                    "senses": [],
                    "etymology": "",
                    "etymology_class": None,
                    "parents": [],
                    "source_lang": None,
                    "derived": [],
                    "related": [],
                    "forms": [],
                }
            # frequency is a property of the word, not of the POS
            card["rank"] = min(card["rank"], rank)
            card["count"] = max(card["count"], count)

            for s in senses:
                if any(x["gloss"] == s["gloss"] and x["pos"] == pos for x in card["senses"]):
                    continue
                card["senses"].append({
                    "pos": pos,
                    "pos_label": POS_LABEL.get(pos, pos),
                    "gloss": s["gloss"],
                    "tags": s["tags"],
                    "cats": s["cats"][:3],
                    "examples": extract_examples(
                        s["sense"], headword=w, own_rank=rank, freq=freq),
                    "links": [x[0] for x in (s["sense"].get("links") or []) if x][:3],
                    "_score": s["score"],
                    # Position in the raw Kaikki file, across all POS entries for
                    # this word. Preserves Wiktionary's own sense ordering so the
                    # content senses can fall back to it (see sense_key).
                    "_src": len(card["senses"]),
                })

            if not card["etymology"] and ety["text"]:
                card["etymology"] = ety["text"]
                card["etymology_class"] = ety["cls"]
                card["source_lang"] = ety["source_lang"]
            for p in ety["parents"]:
                if p not in card["parents"] and p != w:
                    card["parents"].append(p)
            for d in (j.get("derived") or []):
                if d.get("word") and d["word"] != w and d["word"] not in card["derived"]:
                    card["derived"].append(d["word"])
            for r in (j.get("related") or []):
                if r.get("word") and r["word"] not in card["related"]:
                    card["related"].append(r["word"])
            card["forms"] = entry_forms(j) or card["forms"]

    # Order senses in two tiers.
    #
    # Tier 1 - function-word senses (conj/prep/pron/det/num/intj) lead. For these
    # the POS is the entire point: 'e' is 'and' as a conjunction, not a rare
    # noun sense. Within the tier, gloss score orders them, and ties keep
    # Wiktionary's own order so the curated primary sense survives.
    #
    # Tier 2 - content words (adv/noun/verb/adj) keep the RAW FILE ORDER, which
    # is Wiktionary's own sense order. Sorting these by POS discarded that and
    # promoted rare noun senses over the common verb/adj sense: 'dua' became
    # 'sheaf' instead of 'to want'. Ordering by score alone instead promoted
    # the wrong sense for 'të' ('you'). File order fixes the content words
    # without disturbing the function words.
    # One refinement to file order. Kaikki lists a word's homographs as
    # separate entries, and the everyday sense is usually the untagged one
    # while a rare homograph carries a grammatical gender: mot = 'next year'
    # (adv, untagged) versus mot = 'weather' (noun, masculine). File order
    # alone picks 'weather'. So when a word also has an untagged verb or
    # adverb, its gender-tagged noun senses sink below the rest.
    #
    # The demote is deliberately narrow. It needs an untagged verb/adv to
    # fire, so 'mesues' = 'teacher, instructor' (noun, masculine) still leads
    # over its untagged adjective 'instructive' - an adjective does not
    # trigger the demote. Scored against a 61-word hand-checked watchlist
    # (tools/_probe_strategies.py): file order alone 48, this rule 52, and
    # sorting within a POS tier by gloss score only 43 - short glosses win
    # that sort and it promotes the wrong sense, so source order is kept
    # inside the tier.
    def sort_senses(senses):
        has_untagged_va = any(
            s["pos"] in ("verb", "adv")
            and not GENDER_TAGS.intersection(s["tags"])
            for s in senses
        )

        def key(s):
            if s["pos"] in FUNC_POS:
                return (0, FUNC_POS.index(s["pos"]), s["_score"])
            demote = (
                has_untagged_va
                and s["pos"] == "noun"
                and bool(GENDER_TAGS.intersection(s["tags"]))
            )
            return (1, 1 if demote else 0, s["_src"])

        senses.sort(key=key)

    out = []
    for w, c in cards.items():
        sort_senses(c["senses"])
        out.append(c)
    out.sort(key=lambda c: (c["rank"], c["word"]))

    stats["kept"] = len(out)
    stats["families"] = 0
    return out, stats


# ---------------------------------------------------------- word families

def friendly_form_glosses(cards):
    """Rewrite inflected-form glosses for a learner, in place.

    A form card's gloss arrives as grammar ('third-person singular present
    indicative of jam'), which is accurate and close to useless for someone
    learning the language. form_gloss.friendly_gloss turns it into what the
    word does in a sentence ('he/she/it is (from jam, to be)').

    It needs the whole deck, because it reads each lemma's own English gloss,
    which is why this runs after every card has been loaded rather than while
    form cards are being created. Returns (rewritten, kept) counts; a card whose
    gloss cannot be rewritten safely keeps the original.
    """
    lookup = {}
    for c in cards:
        lookup[c["word"]] = {"glosses": [s["gloss"] for s in c.get("senses") or []]}

    rewritten = kept = inferred = 0
    for c in cards:
        senses = c.get("senses") or []
        for s in senses:
            lemma = s.get("is_form_of")
            if not lemma:
                # A word can be a MAIN entry whose only gloss is form-of
                # phrasing: 'qen' is listed with the gloss 'third-person plural
                # simple perfect indicative of jam' and nothing else, so
                # add_form_cards never set is_form_of and this loop skipped it,
                # leaving nine cards on raw dictionary phrasing.
                #
                # form_of_lemma is the gate, and it decides from the GLOSS, not
                # from tags: 'qen' carries no form-of tag, so sense_is_content
                # calls it a content sense and the word is skipped. What
                # actually identifies these entries is that the gloss itself is
                # grammatical ('... indicative of jam').
                #
                # Every sense must be form-of phrasing, so a word that also
                # means something in its own right is left alone: 'qete' is
                # also 'quiet', and its own meaning must keep the card.
                lemmas = []
                for x in senses:
                    g = x.get("gloss")
                    # A semicolon means the gloss states its own meaning and
                    # then adds grammar: 'neve' is glossed 'us; dative of ne'.
                    # Rewriting that drops the dative reading and replaces a
                    # real meaning with the lemma's English ('we'), which
                    # teaches something the card never said. Keep it as-is.
                    if ";" in str(g or ""):
                        lemmas = []
                        break
                    lem = form_senses.form_of_lemma(
                        g, x.get("tags"), words=set(lookup))
                    if not lem:
                        lemmas = []
                        break
                    lemmas.append(lem)
                if not lemmas:
                    continue
                lemma = lemmas[0]
                inferred += 1
            new = form_gloss.friendly_gloss(
                s["gloss"], s.get("pos"), lemma, lookup)
            if new:
                s["gloss"] = new
                s["is_form_of"] = lemma
                rewritten += 1
            else:
                kept += 1
    return rewritten, kept

def build_families(cards):
    """Link words into families using explicit derivation evidence ONLY.

    A word joins the family of a base word only when its etymology text states
    the derivation compositionally ("From marr + -es"). Two sources that
    looked like evidence but are not are deliberately unused:

      * "parents" - extracted from etymology text by parse_etymology(), so it
        contains English gloss words (nuk -> [one, not]). A family edge built
        on it links unrelated words whenever the English word happens to also
        be an Albanian word.
      * "derived" - Wiktionary's loose co-occurrence list. bri ("rib") lists
        bori ("bugle"); zbres ("descend") lists falas, falem, fale.

    Both produced real, visible defects: nuk (the negator "not, don't") was
    filed under not (the noun "swim, swimming"), and the loan bori under the
    inherited bri. Spelling similarity is not a substitute for evidence either
    -- marre ("shame") and marrtë ("twilight") are homographs of marr with
    unrelated meanings, while tmerr ("terror") is a cognate, not a derivative.
    """
    words = {c["word"] for c in cards}
    by_word = {c["word"]: c for c in cards}
    parent = {}

    for c in cards:
        w = c["word"]
        # An inflected form belongs to its lemma's family, so the two unlock
        # together and the learner never meets a form before its base. This is
        # a different kind of link from the etymological one below, which is
        # evidence of derivation; this one is grammatical.
        lemma = form_lemma_of(c)
        if lemma and lemma in words and lemma != w:
            parent.setdefault(w, lemma)
            continue
        for base in derivations_from_text(c.get("etymology", "")):
            # e- (privative prefix) is not e ("and"); see
            # pos_balance.NOT_A_FAMILY_BASE.
            if base in pos_balance.NOT_A_FAMILY_BASE:
                continue
            if base in words and base != w:
                parent.setdefault(w, base)
                break

    def root_of(word):
        seen = {word}
        cur = word
        while cur in parent:
            cur = parent[cur]
            if cur in seen:
                break
            seen.add(cur)
        return cur

    families = defaultdict(list)
    for w in words:
        families[root_of(w)].append(w)
    return parent, dict(families)


# ----------------------------------------------------------------- levels

def by_word_components(cards):
    """{word: [component, ...]} from the per-card components list."""
    return {c["word"]: c.get("components") or [] for c in cards
            if c.get("components")}


def schedule_course(cards, families, components=None, opening=None,
                    main_max_rank=MAIN_MAX_RANK):
    """The main course, then the extended track, as assign_levels() levels.

    The main course is every card ranked up to `main_max_rank`, the curated
    opening, and (transitively) the stems those words are built on, so the
    prerequisite rule holds inside it. Everything else is the extended
    track: scheduled by the same rules, numbered after the main course, and
    marked `extended`. Its stems are all taught already, either in the main
    course or earlier in the track. No card is dropped.
    """
    components = components or {}
    rank_of = {c["word"]: c["rank"] for c in cards}
    main = {w for w, r in rank_of.items() if r <= main_max_rank}
    main |= {w for _, ws in (opening or ()) for w in ws if w in rank_of}
    todo = sorted(main)
    while todo:
        w = todo.pop()
        for c in components.get(w, ()):
            s = c.get("word")
            if c.get("role") == "stem" and s in rank_of and s not in main:
                main.add(s)
                todo.append(s)

    def part(keep):
        fams = {r: [m for m in ms if m in keep] for r, ms in families.items()}
        return ([c for c in cards if c["word"] in keep],
                {r: ms for r, ms in fams.items() if ms})

    main_cards, main_fams = part(main)
    levels = assign_levels(main_cards, main_fams, components=components,
                           opening=opening)
    ext_cards, ext_fams = part(set(rank_of) - main)
    if ext_cards:
        for lvl in assign_levels(ext_cards, ext_fams, components=components,
                                 begun=set(main_fams)):
            lvl[7]["extended"] = True
            levels.append(lvl)
    return levels


def assign_levels(cards, families, per_level=9, max_families=6,
                  components=None, opening=None, begun=()):
    """Levels are sessions of whole word families, in prerequisite order.

    Three rules, in priority order:

      1. A stem is never taught after the word built on it. esëll is e- + sillë, so
         sille must unlock no later than esell, even though sille is the
         rarer word. This is the kanji bargain applied to whole words: the
         component comes first because it explains the card.
      2. Within a level, a family is never split. A root and its derivations
         unlock together, so studying a level teaches a word group rather
         than an arbitrary frequency slice. The one exception is a family's
         rare tail ("root first, tail later"): its rank > 1200 members come
         back later as "root (rarer words)", once the course reaches them.
      3. A level is a session, not a single item: families are packed until
         per_level words are reached, at most max_families of them.

    Families too large for one session spill into continuation levels that
    repeat the root ("krye 2/3") so a split family stays one lesson rather
    than a pile of orphans.

    Roots are ordered by prerequisite-respecting rank, not by raw frequency.
    A rare stem that many words depend on outranks the common word that
    happens to sit above it in the corpus.

    `components` is {word: [{"word":..., "role":...}, ...]}. Only stems
    (role "stem") create prerequisites; a prefix is already the family root,
    so it is displayed but never re-ordered.

    `opening` is the hand-curated opening (tools/opening_levels.LEVELS): a
    list of (title, words) that become levels 1..n as written. The scheduler
    runs on what is left. A family the opening only partly teaches comes
    back later at its own frequency, on a level that lists it under
    `continues`.

    `begun` names families an earlier track already taught (see
    schedule_course()); their levels here are titled "root (more)".
    """
    rank_of = {c["word"]: c["rank"] for c in cards}

    # Teaching priority inside a family. `jam` has 21 members, and a
    # frequency sort opens that family with `qenka`/`qenke` (a colloquial
    # present) and buries the subjunctive and the perfect. Sorting by
    # tense first puts the everyday present at the front of the lesson.
    by_word_card = {c["word"]: c for c in cards}

    components = components or {}

    def stems_of(word):
        return [c["word"] for c in components.get(word, ())
                if c.get("role") == "stem"]

    fam_of = {}
    for root, members in families.items():
        for m in members:
            fam_of[m] = root

    # ---- the hand-curated opening ----------------------------------------
    # Levels 1..n are set by theme in tools/opening_levels.py (greetings,
    # pronouns, jam/kam, numbers, family, food...), because no frequency
    # list is a syllabus for a first week. Everything below schedules the
    # rest. A curated word's stem is curated no later than it (plan()
    # checks), so no edge into the opening is ever unmet.
    curated = []
    opened = set()
    if opening:
        curated = opening_levels.plan(opening, set(rank_of), fam_of,
                                      stems_of, per_level, max_families)
        opened = {w for _, ws in curated for w in ws}
        families = {r: [m for m in ms if m not in opened]
                    for r, ms in families.items()}
        families = {r: ms for r, ms in families.items() if ms}
    opened_fams = {fam_of[w] for w in opened}

    score = {}
    for root, members in families.items():
        got = [rank_of[m] for m in members if m in rank_of]
        if got:
            score[root] = min(got)

    # ---- the opening is for content, not grammatical scaffolding --------
    #
    # The frequency list is OpenSubtitles, so ranking by frequency and
    # taking the top produces a wall of function words BY CONSTRUCTION: of
    # the 45 most frequent tokens, exactly one is a plain content noun.
    # Level 1 was therefore te (rank 1, conjunction), ne (rank 3,
    # conjunction), babi, zemer, re -- two conjunctions out of five cards.
    #
    # The brief is that grammar is taught elsewhere, so closed-class words
    # should not spend the scarce first sessions. Conjunctions, prepositions,
    # determiners and numerals are deferred. Verbs are NOT: a paradigm is
    # vocabulary the learner meets in situ, and conjugations stay.
    #
    # Expressed as a synthetic rank, the same device the early-noun boost
    # uses below. Setting score=0 would send every deferred root to the
    # absolute front and displace the content words this makes room for.
    #
    # Bounded by count, not banned outright. The opening genuinely needs
    # dhe (12), nje (11) and se (15); without them a learner cannot build a
    # sentence. The most frequent keep their natural rank; the rest are
    # pushed past the opening, still taught, just later. No card is dropped.
    #
    # Admission is by NAMED SET, not by a frequency budget. Budgeting by
    # frequency admitted the six most frequent closed-class roots -- te,
    # ne, do, me, qe, nje, every one inside rank 1-11 -- which are exactly
    # the words that made level 1 a wall of grammar. See
    # opening_policy.OPENING_FUNCTION_WORDS for the set and the reasoning.
    # A family is deferred only when its ROOT is a closed-class word that is
    # not admitted. Testing the root rather than any member is what keeps
    # conjugations in the opening.
    #
    # The first version asked whether ANY member was a blocked function word,
    # and that sent `eshte` -- rank 6, the copula, a conjugation the brief
    # keeps -- to level 186, because its family `jam` also holds `meqenese`
    # ("because", a conjunction) and `qenie` ("existence", a noun). One
    # conjunction in the family banished the whole paradigm, taking jam,
    # jemi, jeni and qenka with it. The brief is explicit that conjugations
    # remain, so a verb family is never deferred for a member that merely
    # reads as closed class; only a family NAMED after a function word is.
    by_word_fn = {c["word"]: c for c in cards}
    beyond = []
    for root in sorted(families, key=lambda r: (score.get(r, 10 ** 9), r)):
        card = by_word_fn.get(root) or {}
        if not opening_policy.is_function_word(card):
            continue
        if opening_policy.admits_to_opening(root):
            continue
        # A family is atomic, so deferring its head hands the opening slot to
        # its rare tail. `nje` and `me` are admitted whole for that reason:
        # deferring them pushed njezet, njesi and mjaftoj (rank 42540) into
        # the opening in place of the head. See
        # opening_policy.OPENING_FUNCTION_FAMILIES.
        if opening_policy.admits_family_to_opening(root):
            continue
        # Pushed past the opening by a synthetic rank beyond every real one.
        # The word is still taught, just later: nothing is dropped.
        score[root] = DEFER_MAX_ROOT_RANK + 1 + len(beyond)
        beyond.append(root)
    # Spread, not stacked. Every deferred root used to get a rank just past
    # DEFER_MAX_ROOT_RANK, so all of them -- të, që, nga, kjo, ky, pa, pas,
    # deri, prej... 38 top-200 words -- arrived together at L165-179, a
    # wall of grammar after a hundred levels without it (RECOMMENDATIONS.md
    # section 3.2). Each is now woven into the natural order instead: after
    # the scheduler's first DEFER_SPREAD_AFTER families, one every
    # DEFER_SPREAD_EVERY families, most frequent first. That is about one
    # per level. A root with nothing left to follow keeps its old rank.
    natural = sorted((r for r in families if r not in set(beyond)
                      and r in score),
                     key=lambda r: (score[r], r))
    for i, root in enumerate(beyond):
        at = DEFER_SPREAD_AFTER + i * DEFER_SPREAD_EVERY
        if at < len(natural):
            score[root] = score[natural[at]] + 0.5
    if beyond:
        print("  %d closed-class roots deferred past the opening: %s"
              % (len(beyond), " ".join(sorted(beyond))))


    # Item 4: pull pictureable nouns into the opening levels.
    #
    # The boost is expressed as a synthetic rank rather than as score=0.
    # Setting score=0 sent all 50 promoted roots to the absolute front of the
    # queue and produced an opening that was 88.8% nouns with `te` and `nuk`
    # pushed to level 9 -- strictly worse than the 55%-verb problem it was
    # meant to fix. A dry run missed that because it appended nouns to an
    # existing mix, whereas a score of 0 displaces every other family.
    #
    # Instead each promoted noun is given a synthetic rank that places it at
    # its target slot in the natural frequency order. Frequency ordering is
    # preserved everywhere else, prerequisites still dominate (the topological
    # sort below is unchanged), and the nouns are spread through the window
    # rather than forming a wall at the front.
    early_nouns = []
    for root, members in families.items():
        if len(members) != 1:
            continue
        card = by_word_card.get(members[0]) or {}
        if pos_balance.promote(card, None, 1):
            early_nouns.append((score.get(root, 10 ** 9), root))
    early_nouns.sort()

    if early_nouns:
        # Natural order, and the nouns chosen to join it.
        natural = sorted(families, key=lambda r: (score.get(r, 10 ** 9), r))
        # The window is sized in WORDS, not in families. It used to be a
        # fixed 20 families, which only worked while the opening was
        # dominated by very large families (jam alone had 21 members, so 20
        # families covered 158 words). Teaching the common function words
        # early re-homes compounds to their stem families, which makes the
        # opening families smaller -- the same 20 families then held 96
        # words, and the noun rebalance quietly lost its footing.
        #
        # Sized in words it states its real intent: cover the first ten
        # levels with room to spare, whatever shape the families are in.
        # The window is the first ten levels' worth of vocabulary, measured in
        # WORDS. It used to be a fixed 20 families, which only worked while the
        # opening was dominated by very large families (jam alone had 21
        # members, so 20 families covered 158 words). Teaching the common
        # function words early re-homes compounds to their stem families,
        # making the opening families smaller -- the same 20 families then
        # held 96 words and the noun rebalance quietly lost its footing.
        window = []
        win_words = 0
        for r in natural:
            if window and win_words >= pos_balance.WINDOW_WORDS:
                break
            window.append(r)
            win_words += len(families[r])
        win_nouns = 0
        for r in window:
            for m in families[r]:
                if pos_balance.headline_pos(by_word_card.get(m) or {}) == 'noun':
                    win_nouns += 1
        room = pos_balance.quota(win_words, win_nouns)
        chosen = [r for _, r in early_nouns[:room]]
        if chosen:
            # Pace the nouns across the opening window only. Spreading them
            # over the whole frequency list placed them too late to help the
            # first ten levels, which is where the noun floor is measured.
            for r, new_rank in pos_balance.spread(chosen, window).items():
                score[r] = new_rank
            print("  early window: %d words, %d nouns (%.0f%%); target %.0f%%; "
                  "weaving in %d pictureable nouns"
                  % (win_words, win_nouns,
                     100.0 * win_nouns / max(1, win_words),
                     100.0 * pos_balance.TARGET_NOUN_SHARE, len(chosen)))

    # ---- the opening must not be crowded out by a family's rare tail ------
    #
    # A family is taught whole, which is right for a root and its
    # derivations but has a cost the frequency sort cannot see: the family
    # also owns its inflected forms, its productive compounds and its
    # archaisms, and those inflate it far past the common word that named
    # it. Measured on the opening:
    #
    #   do  (rank 4)   8 members, median rank 22083 -- doemos, medoemos,
    #                   domosdoshem, domosdoshmeri, ndopak
    #   një (rank 11)   8 members, median rank 3390  -- njëzet, njësi, mënjanë
    #   me  (rank 14)   4 members, median rank 3227  -- mjaftoj (rank 42540)
    #   jam (rank 6)   22 members, median rank 258
    #
    # Fifteen of the sixty-nine words in levels 1-10 had rank > 2000, and
    # rare words crowded out common ones: doemos (30516) and qeshe (15706)
    # sat in level 2 and 4 while mire (rank 21) waited until level 13, past
    # shume, por and kjo.
    #
    # So a family is split by frequency for scheduling purposes only. The
    # common head of a family -- the word that earned it its place, plus its
    # everyday forms -- competes for the opening; the rare tail is scheduled
    # after it. Nothing is dropped and no family is broken: a learner who
    # reaches the tail still gets it as a whole, it simply no longer competes
    # for a level-1 slot against words they meet in their first week.
    #
    # The cut is deliberately generous (OPENING_MEMBER_MAX_RANK). The point
    # is not to prune the deck, it is to stop rank-30000 words sitting beside
    # rank-4 ones in a first session. Where the tail goes is decided below,
    # under "root first, tail later".
    # head_members[root] = the members that teach the family in its first
    # session, when it has been split. Read back by the deps pass below.
    deferred_units_head = {}
    for root, members in families.items():
        common = [m for m in members
                  if rank_of.get(m, 10 ** 9) <= OPENING_MEMBER_MAX_RANK]
        if not common or len(common) == len(members):
            continue
        # Every family with a rare tail is a candidate, including the ones at
        # the front of the course. Bars that used to keep do, jam, nje and me
        # whole existed because a tail was placed in the level right after
        # its head, so splitting a family in the opening only moved doemos
        # (rank 30516) from level 2 to level 3. A tail is now scheduled at
        # its OWN frequency, so splitting does move it out of the opening.
        deferred_units_head[root] = list(common)

    # ---- topological order over families ---------------------------------
    # A family cannot unlock before the family holding a stem one of its
    # members is built from. This has to be a real topological sort, not a
    # depth sort: neper (family ne) needs per (family per), and both roots
    # are stemless, so they share a depth and frequency alone decides --
    # which put neper first. A depth tie cannot resolve that; an explicit
    # edge between the two families can.
    #
    # Among families ready at the same moment the most frequent goes first,
    # so the course still reads as "common words early" wherever the
    # etymology imposes no order.
    # A family cannot unlock before the family holding a stem one of its
    # HEAD members is built from. The HEAD, specifically.
    #
    # Scoring this over the whole family gated common words behind their own
    # rare tail. per (rank 13) shipped at L276 because its tail member
    # pranvere is "prane + vere", so vere -- wine, rank 1393 -- became a
    # prerequisite for the entire family and per waited for it at position
    # 506 of 3013. A learner meets per in their first sentence; they do not
    # meet wine for another fifty lessons. The head is the session that
    # teaches the family, so only the head's stems may hold it back, and the
    # tail is placed after it with its own stems already taught.
    deps = {}
    for root, members in families.items():
        need = set()
        head_members = deferred_units_head.get(root) or members
        for m in head_members:
            for s in stems_of(m):
                sf = fam_of.get(s)
                if sf is not None and sf != root and s not in opened:
                    need.add(sf)
        deps[root] = need

    # dependents[f] lists the families that are waiting on f, so releasing
    # a family only touches the edges that actually point at it.
    dependents = {r: [] for r in deps}
    for root, need in deps.items():
        for dep in need:
            dependents[dep].append(root)

    remaining = {r: len(deps[r]) for r in deps}
    ready = [r for r in deps if remaining[r] == 0]
    ready.sort(key=lambda r: (score.get(r, 10 ** 9), r))

    ordered = []
    while ready:
        root = ready.pop(0)
        ordered.append(root)
        for other in dependents[root]:
            remaining[other] -= 1
            if remaining[other] == 0:
                ready.append(other)
        ready.sort(key=lambda r: (score.get(r, 10 ** 9), r))

    # Cyclic etymologies starve the queue above, and they are real rather
    # than parser noise: dalengadale is dale- + nga, while ngadale is nga- +
    # dale, so those two families need each other and no order satisfies both.
    #
    # No ordering can satisfy a cycle, so the leftovers are appended in
    # frequency order rather than dropped. Everything outside a cycle is
    # already placed above and fully respects its prerequisites; the words
    # left late here are the ones where late is the lesser of two wrongs.
    if len(ordered) < len(deps):
        placed = set(ordered)
        rest = sorted((r for r in deps if r not in placed),
                      key=lambda r: (score.get(r, 10 ** 9), r))
        ordered.extend(rest)
        print("  %d families in a stem cycle (mutual borrowing, e.g. "
              "dalengadale <-> ngadale); appended by frequency" % len(rest))

    # A family whose rare tail would fill the opening is taught in two passes:
    # the common head competes on frequency, and the tail follows as its own
    # unit once the head has been placed. See "the opening must not be crowded
    # out by a family's rare tail" above.
    #
    # The head keeps the root and everything a learner meets in ordinary
    # speech. The tail is placed immediately after the whole course has been
    # scheduled by frequency, so it interleaves with other mid-frequency
    # vocabulary rather than piling up at the end. Splitting on frequency
    # rather than on the family's own ordering also keeps teaching_order()'s
    # tense-first sort intact inside each pass.
    # The families that compete for the opening: the most common ones, in
    # frequency order, until their common words would fill the opening
    # twice over. Only these shed a tail of one or two words; splitting
    # every family under rank 900 the same way cost 150 extra levels.
    opening_families = set()
    filled = 0
    for root in sorted(families, key=lambda r: (score.get(r, 10 ** 9), r)):
        if filled >= 2 * pos_balance.WINDOW_WORDS:
            break
        opening_families.add(root)
        filled += sum(1 for m in families[root]
                      if rank_of.get(m, 10 ** 9) <= OPENING_MEMBER_MAX_RANK)

    deferred_units = []
    defer_at = {}
    for root in ordered:
        members = families[root]
        if root not in deferred_units_head:
            continue
        common = [m for m in members
                  if rank_of.get(m, 10 ** 9) <= OPENING_MEMBER_MAX_RANK]
        # The root ALWAYS leads the head, even when it is rarer than its own
        # inflected form. levoj heads a family whose common member is lexuar
        # (rank 1170) while levoj itself is rank 1814; filtering the root out
        # of the tail without putting it back in the head silently deleted 24
        # cards (lexoj, shkruaj, mesoj, fitoj, uroj and 19 others) -- the
        # family's own name is the one word it cannot afford to lose.
        if root in members and root not in common:
            common = [root] + common
        cset = set(common)
        rare = [m for m in members if m not in cset]
        # A family that competes for the opening sheds any rare tail, even a
        # single word: mjaftoj (rank 42540) beside me (rank 14) is exactly
        # the stray the opening must not hold. Elsewhere one rare member
        # costs nothing, and a tail of its own would cost a session, so the
        # OPENING_MIN_DEFERRED bar still applies.
        need = 1 if root in opening_families else OPENING_MIN_DEFERRED
        if len(rare) < need:
            continue
        # The family is NOT shrunk: every member keeps its family, so the head
        # and the tail stay ONE family. Only the ORDER changes: the common
        # members are listed first and the rare ones after, so the split point
        # falls between them. family_units() below does the numbering.
        deferred_units.append((root, rare, score.get(root, 10 ** 9), root))
        defer_at[root] = len(common)

    if deferred_units:
        n_deferred = sum(len(m) for _, m, _, _ in deferred_units)
        print("  %d rare family members across %d families held back "
              "from the opening" % (n_deferred, len(deferred_units)))

    # ---- root first, tail later ------------------------------------------
    #
    # A split family's rare tail used to follow its head in the very next
    # level, so a family at the front of the course carried its tail into
    # the opening: do (rank 4) taught doemos (30516) and medoemos (22302) in
    # level 2, jam filled level 5 with qenke, qenie, meqenese and qeshe, and
    # une ("I", rank 16) was pushed to level 11.
    #
    # The tail is now scheduled in its own frequency band: it is emitted
    # just before the first family whose rank -- and the rank of every
    # family after it -- is above the tail's most common member. It also
    # waits for the families holding its own stems, so prerequisites still
    # hold. The head teaches the root; the tail level ("do 2/2") comes back
    # to the family once the learner's frontier reaches those words.
    rare_of = {r_root: set(rare) for r_root, rare, _, _ in deferred_units}

    def family_units(root):
        """The (members, part, nparts, resumes) units of one family."""
        rare_set = rare_of.get(root, set())
        # teaching_order() sorts a family by teaching priority first (the
        # everyday present before the subjunctive), which is right WITHIN a
        # session. A deferred family additionally needs its common members
        # listed before its rare ones, so the rare set is keyed first and
        # the teaching order still decides everything inside each half.
        members = sorted(
            families[root],
            key=lambda w: (1 if w in rare_set else 0,
                           teaching_order.level_key(
                               by_word_card.get(w) or {}, is_root=(w == root)),
                           rank_of.get(w, 10 ** 9), w),
        )
        cut = defer_at.get(root)
        if cut is None:
            nparts = max(1, -(-len(members) // per_level))
            return [(members[i:i + per_level], i // per_level, nparts, False)
                    for i in range(0, len(members), per_level)], []
        # The split point must land ON a part boundary, or the rare members
        # would share a session with the common ones.
        # Head and tail are numbered as two runs: the head is taught like any
        # family ("per 1/2", or just "do"), and the tail is its own run of
        # levels marked as the family's rarer words ("do (rarer words)").
        head_parts = max(1, -(-cut // per_level))
        tail_parts = max(1, -(-(len(members) - cut) // per_level))
        head, tail = members[:cut], members[cut:]
        head_units = [(head[i * per_level:(i + 1) * per_level], i,
                       head_parts, False) for i in range(head_parts)]
        tail_units = [(tail[i:i + per_level], j, tail_parts, True)
                      for j, i in enumerate(range(0, len(tail), per_level))]
        return head_units, tail_units

    # The frontier is the rarest family placed so far. The order is
    # topological, so a common family can follow a rarer one it depends on;
    # the running maximum ignores those and tracks how far into the
    # frequency list the learner has actually got.
    big = 10 ** 9
    pending = []   # (tail rank, root, stem families, tail units)
    emitted = set()
    units = []     # (root, members, part, nparts, resumes)
    frontier = 0

    def release(frontier):
        for item in sorted(pending):
            rank, root, needs, tunits = item
            if rank < frontier and needs <= emitted:
                units.extend((root,) + u for u in tunits)
                pending.remove(item)

    for root in ordered:
        frontier = max(frontier, score.get(root, big))
        release(frontier)
        head_units, tail_units = family_units(root)
        units.extend((root,) + u for u in head_units)
        emitted.add(root)
        if tail_units:
            tail_words = [w for u in tail_units for w in u[0]]
            needs = {fam_of[s] for w in tail_words for s in stems_of(w)
                     if fam_of.get(s) not in (None, root) and s not in opened}
            pending.append((min(rank_of.get(w, big) for w in tail_words),
                            root, needs, tail_units))
    # Whatever is left waits on a stem cycle or is rarer than everything
    # else; it goes last, most common first.
    for _, root, _, tunits in sorted(pending):
        units.extend((root,) + u for u in tunits)

    # Pack consecutive units into session-sized levels.
    #
    #   1. A continuation unit (part > 0) always gets a level to itself, so a
    #      split family is not mislabelled or scattered.
    #   2. A family never contributes two parts to one level.
    #   3. Otherwise pack whole families up to per_level words and
    #      max_families roots.
    levels = []
    for title, ws in curated:
        roots = sorted({fam_of[w] for w in ws})
        levels.append((roots[0] if len(roots) == 1 else "", list(ws), title,
                       len(roots), 1, 1, False, {"opening": True}))
    continued = set()
    cur_words, cur_roots, cur_part, cur_sizes = [], [], {}, []
    cur_tail = False

    def flush():
        nonlocal cur_words, cur_roots, cur_part, cur_sizes, cur_tail
        if not cur_words:
            return
        if len(cur_roots) == 1:
            root = cur_roots[0]
            part, nparts = cur_part[root][0] + 1, cur_part[root][1]
        else:
            root = ""
            part, nparts = 1, 1
        if cur_tail:
            title = "%s (rarer words)" % root
            if nparts > 1:
                title += " %d/%d" % (part, nparts)
        elif root in opened_fams:
            # The rest of a family the curated opening began ("jam" opens
            # with the present tense; ishte, qenë... come back here).
            title = "%s (continued)" % root
            if nparts > 1:
                title += " %d/%d" % (part, nparts)
        elif root in begun:
            # More of a family the main course taught; the root itself is
            # not on this level.
            title = "%s (more)" % root
            if nparts > 1:
                title += " %d/%d" % (part, nparts)
        elif nparts == 1:
            # Name at most TITLE_ROOTS roots and count only the ones left out,
            # so "+N" is the number actually hidden (it used to be len - 2
            # while every root was still listed).
            title = root if root else ", ".join(
                "%s (more)" % r if r in begun else r
                for r in cur_roots[:TITLE_ROOTS])
        else:
            title = "%s %d/%d" % (root, part, nparts)
        if not root and len(cur_roots) > TITLE_ROOTS:
            title += " +%d" % (len(cur_roots) - TITLE_ROOTS)
        # The first level after the opening that brings back a family the
        # opening began. The validator lets the family resume here.
        cont = sorted(r for r in cur_roots
                      if r in opened_fams and r not in continued
                      and not cur_tail)
        continued.update(cont)
        levels.append((root, list(cur_words), title, len(cur_roots), part,
                       nparts, cur_tail and part == 1,
                       {"continues": cont} if cont else {}))
        cur_words, cur_roots, cur_part, cur_sizes = [], [], {}, []
        cur_tail = False

    for root, members, part, nparts, tail in units:
        # Option 2: a multi-member family teaches a root plus its
        # derivations, so it holds the level alone. Singletons have no group
        # lesson and pack up to the session target as before. A continuation
        # part is always alone too, so a split family stays one lesson.
        #
        # Sizes are the units', not the families': a split family's head is
        # what is taught here, so do (one common word, seven rare) packs like
        # the singleton it now is instead of holding a level on its own.
        blocked = cur_words and (
            part > 0
            or tail
            or not pack_shape.may_join(cur_sizes, len(members))
            or len(cur_words) + len(members) > per_level)
        if blocked:
            flush()
        if root not in cur_part:
            cur_part[root] = (part, nparts)
            cur_roots.append(root)
            cur_sizes.append(len(members))
        cur_words.extend(members)
        cur_tail = tail
        # A tail level always stands alone, so the level that resumes a
        # family can say so ("resumes") and the validator can check it.
        if part > 0 or tail:
            flush()
    flush()

    return levels


def word_object(w, c, root, corpus_examples):
    """The level-file card for word `w`, built from its build-time card `c`.

    `_tier` rides along for the in-level sort and is removed before writing.
    """
    head = c["senses"][0] if c["senses"] else None
    return {
        "id": w,
        "sq": w,
        "en": head["gloss"] if head else "",
        "glosses": [s["gloss"] for s in c["senses"]],
        "pos": [s["pos"] for s in c["senses"]],
        "pos_labels": [s["pos_label"] for s in c["senses"]],
        # _score/_src are build-time only; the app never needs them
        "sense_detail": [{k: v for k, v in s.items()
                          if k not in ("_score", "_src")}
                         for s in c["senses"]],
        "rank": c["rank"],
        "count": c["count"],
        "family": c.get("family", w),
        "is_root": c.get("family", w) == w,
        "etymology": c["etymology"],
        "etymology_class": c["etymology_class"],
        "source_lang": c["source_lang"],
        # Item 3: the source-language form, e.g. "from Latin soca".
        # The deck already shows components this way ("from e- +
        # sille"); a cognate is the historical equivalent.
        "cognate": cognates.cognate_line(w, c["etymology"], c["source_lang"]),
        "parents": c["parents"][:3],
        "components": c.get("components") or [],
        "derived": c["derived"][:8],
        "related": c["related"][:5],
        "forms": c["forms"],
        # Corpus fallback, shaped like a sense example so the
        # existing exampleForSense() logic reads it unchanged.
        "corpus_example": corpus_examples.get(w),
        "_tier": teaching_order.level_key(c, is_root=(w == root))[0],
    }


def write_levels(levels, by_word, corpus_examples):
    """Write the level files, course.json and index.json for `levels`.

    `levels` is assign_levels() output and `by_word` maps each word to its
    build-time card. tools/relevel.py calls this too, with cards read back
    from the shipped level files, so the two paths cannot drift apart.
    Returns the level objects, in order.
    """
    os.makedirs(LEVELS_DIR, exist_ok=True)
    for f in os.listdir(LEVELS_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(LEVELS_DIR, f))

    # Zero-pad to a width that fits the largest level number. A fixed %02d
    # breaks once there are 100+ levels: "level_100" then sorts before
    # "level_11", so any consumer that globs and sorts the directory by name
    # gets levels out of order.
    lvl_width = max(2, len(str(len(levels))))

    level_objs = []
    for i, (root, words, title, nfam, part, nparts, resumes, meta) in enumerate(levels, 1):
        objs = []
        for w in words:
            objs.append(word_object(w, by_word[w], root, corpus_examples))
        # Order within a level is the teaching order assign_levels() chose
        # (family members sorted by tense/register tier, then frequency).
        # Re-sorting by raw rank here silently undid that work: the `jam`
        # family came out byte-identical to the frequency order, which is
        # how the tier sort was found to be a no-op in practice.
        objs.sort(key=lambda o: (o["_tier"], o["rank"]))
        # _tier exists only to drive that sort. The level-file contract is
        # that no build-time field ships, so drop it before writing.
        for o in objs:
            del o["_tier"]
        # A single-family level is named after its root, the way a Wanikani
        # level is named after the radical it unlocks; a split family keeps
        # the root and gains a "2/3" marker. A multi-family level lists the
        # roots it contains, capped at two plus a count.
        root_gloss = (by_word[root]["senses"][0]["gloss"]
                      if root and by_word[root]["senses"] else "")
        lvl = {
            "level": i,
            "title": title,
            "root": root,
            "root_gloss": root_gloss,
            "part": part,
            "parts": nparts,
            "word_count": len(objs),
            "families": sorted({o["family"] for o in objs}),
            "pos_mix": dict(Counter(p for o in objs for p in o["pos"])),
            "words": objs,
        }
        # The first level of a family's rare tail, scheduled later than its
        # head ("root first, tail later"). The validator lets exactly these
        # continuations follow a gap.
        if resumes:
            lvl["resumes"] = True
        # A curated opening level (tools/opening_levels.py), and the families
        # this level brings back after the opening began them.
        if meta.get("opening"):
            lvl["opening"] = True
        if meta.get("continues"):
            lvl["continues"] = meta["continues"]
        # The optional extended track after the main course (schedule_course).
        if meta.get("extended"):
            lvl["extended"] = True
        level_objs.append(lvl)

    # Breakdown glosses, transparency and pattern notes need the whole course
    # in order (a pattern lands on the level of its third clear example), so
    # the level files are written only after every level exists.
    patterns_at = affixes.annotate_levels(level_objs)
    for lvl in level_objs:
        with open(os.path.join(LEVELS_DIR, "level_%0*d.json"
                               % (lvl_width, lvl["level"])),
                  "w", encoding="utf-8") as fh:
            json.dump(lvl, fh, ensure_ascii=False, indent=1)

    course = {
        "title": "Albanian Roots & Families",
        "language": "sq",
        "source": {
            "dictionary": "Kaikki.org (wiktextract of English Wiktionary)",
            "frequency": "hermitdave/FrequencyWords (OpenSubtitles2018, 2018 build)",
        },
        # The app derives level-file names from this width, so publishing it
        # here keeps the two in lockstep (a hardcoded padStart broke at 1000).
        "level_file_width": lvl_width,
        "level_count": len(level_objs),
        # Levels 1..main_level_count are the main course; the rest are the
        # optional extended track.
        "main_level_count": sum(1 for l in level_objs
                                if not l.get("extended")),
        "word_count": sum(l["word_count"] for l in level_objs),
        # title/root/part/parts ride along so the level map can label each
        # level with its root without loading all 184 level files.
        "levels": [{"level": l["level"], "word_count": l["word_count"],
                    "families": len(l["families"]),
                    "title": l["title"], "root": l["root"],
                    "root_gloss": l["root_gloss"],
                    "part": l["part"], "parts": l["parts"],
                    **({"extended": True} if l.get("extended") else {})}
                   for l in level_objs],
    }
    affixes.set_index_patterns(course["levels"], patterns_at)
    with open(os.path.join(OUT, "course.json"), "w", encoding="utf-8") as fh:
        json.dump(course, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(course["levels"], fh, ensure_ascii=False, indent=1)
    return level_objs


# ------------------------------------------------------------------- main

def main():
    kaikki = os.path.join(RAW, "kaikki_albanian.jsonl")
    freqp = os.path.join(RAW, "sq_50k.txt")
    for p in (kaikki, freqp):
        if not os.path.exists(p):
            print("MISSING:", p, "- run tools/fetch_sources.py first", file=sys.stderr)
            return 2

    print("loading frequency list...", flush=True)
    freq = load_freq(freqp)
    print("  %d distinct words" % len(freq))

    global ORTHO
    with open(kaikki, encoding="utf-8") as fh:
        known = orthography.known_words(json.loads(line) for line in fh if line.strip())
    ORTHO = orthography.Gate(known, {w: r for w, (r, _) in freq.items()})

    print("parsing dictionary...", flush=True)
    cards, stats = load_dict(kaikki, freq)
    print("  orthography gate: %d Wiktionary examples rejected"
          % len(ORTHO_REJECTED))
    print("  %d cards from %d sq entries" % (stats["kept"], stats["sq_total"]))
    for k in ("skipped_pos", "skipped_shape", "skipped_nogloss", "skipped_notfreq", "skipped_excluded", "parse_error"):
        if stats.get(k):
            print("  %-16s %d" % (k, stats[k]))

    # Inflected forms the deck would otherwise never teach. Runs after
    # load_dict so the set of real lemmas is known, and before build_families
    # so each form can join its lemma's family and unlock alongside it.
    added = add_form_cards(cards, kaikki, freq, max_rank=FORM_CARD_MAX_RANK)
    if added:
        print("  +%d inflected-form cards (rank <= %d), now %d cards"
              % (len(added), FORM_CARD_MAX_RANK, len(cards)))

    # The whole deck now exists, so each form can be glossed using the
    # English meaning of its own lemma.
    n_rw, n_keep = friendly_form_glosses(cards)
    if n_rw:
        print("  learner glosses: %d rewritten, %d kept as-is" % (n_rw, n_keep))

    n_fixed = gloss_overrides.apply(cards, lambda p: POS_LABEL.get(p, p))
    print("  reviewed gloss fixes: %d headlines changed" % n_fixed)

    # Core words Wiktionary has no entry for (pra, ndonjë, sikur...). After
    # the form cards and gloss fixes, which only rewrite Wiktionary data, and
    # before families, so a hand-added form (falni) joins its lemma's family.
    hand = added_words.apply(cards, freq, lambda p: POS_LABEL.get(p, p),
                             ALPHABET_RE)
    print("  +%d hand-added core words, now %d cards" % (len(hand), len(cards)))

    # Reference sentences from human-translated corpora. Absent file is fine:
    # the course then ships Wiktionary examples only, exactly as before.
    corpus_examples = {}
    if os.path.exists(CORPUS_EXAMPLES_PATH):
        with open(CORPUS_EXAMPLES_PATH, encoding="utf-8") as fh:
            corpus_examples = json.load(fh)
        for w in sorted(corpus_examples):
            if gloss_overrides.corpus_overridden(w):
                del corpus_examples[w]
                continue
            bad = ORTHO.problems(corpus_examples[w]["sq"], w)
            if bad:
                ORTHO_REJECTED.append(("corpus", w, corpus_examples[w]["sq"], bad))
                del corpus_examples[w]
        print("corpus reference sentences: %d" % len(corpus_examples))
        print("  orthography gate: %d corpus sentences rejected"
              % sum(1 for r in ORTHO_REJECTED if r[0] == "corpus"))
    else:
        print("no corpus_examples.json - Wiktionary examples only")

    print("building word families...", flush=True)
    parent, families = build_families(cards)
    multi = {r: m for r, m in families.items() if len(m) > 1}
    print("  %d families, %d with >1 member" % (len(families), len(multi)))

    # Components are resolved AFTER families but BEFORE levels, because a
    # component must be a word the course actually teaches (hence the full
    # deck as the word set), and because assign_levels() schedules stems
    # ahead of the words built on them.
    by_word = {c["word"]: c for c in cards}
    for root, members in families.items():
        for m in members:
            by_word[m]["family"] = root

    all_words = {c["word"] for c in cards}
    n_comp = 0
    for c in cards:
        comps = components_of(c.get("etymology", ""), all_words)
        c["components"] = [{"word": w, "role": r} for w, r in comps]
        if comps:
            n_comp += 1
    print("  %d cards with components" % n_comp)

    # --- Function-word rescue, BEFORE level assignment.
    #
    # A word that supplies only a PREFIX to a compound is not a member of
    # that compound family; the compound belongs to its stem. Filing it there
    # made the family inherit an edge onto the stem, so a common word could
    # not unlock until a rarer stem was ready: esell (stem sille, rank 30157)
    # put e (rank 2) at L652. Re-home such compounds to their stem family.
    #
    # A family whose own root is used only as a prefix, across members built
    # on many unrelated stems, is a prefix bucket rather than a family: per
    # held 64 members over 42 stems, each edge individually correct, together
    # enough to hold per (rank 13) back to L739. Detach the bare prefix.
    #
    # Both moves only move a word between families or free a prefix; no word
    # is dropped, and every compound still follows its own stem.
    rank_of = dict((c["word"], c["rank"]) for c in cards)
    fam_of = {}
    for root, members in families.items():
        for m in members:
            fam_of[m] = root
    comps_of = by_word_components(cards)
    BIG = 10 ** 9

    def rk(w):
        return rank_of.get(w, BIG)

    # Frozen before any re-homing, so the comparison below cannot depend on
    # how far the loop has progressed. See the note on MIN_FAMILY_RANK.
    MIN_FAMILY_RANK = {}
    for r, ms in families.items():
        MIN_FAMILY_RANK[r] = min(rk(m) for m in ms)

    rehomed = 0
    for root in sorted(families):
        members = families[root]
        if len(members) < 2:
            continue
        # Read the FROZEN minimum, not the live one. Reading the live list
        # made the decision depend on iteration order: family `as` holds
        # `as` (rank 164) and `atje` (rank 97), and `atje` -- "a- + -tje", a
        # prefix compound on the stem `as` -- is itself re-homed out earlier
        # in this same loop. Whether it had already left when the loop
        # reached `as` depended on dict iteration order, so root_rank was 97
        # under one hash seed and 113 under another. That flipped the fate of
        # asgje, askush and asnje, and the differing edge set moved 460 words
        # between levels 143 and 257.
        root_rank = MIN_FAMILY_RANK[root]
        for m in list(members):
            if m == root or fam_of.get(m) != root:
                continue
            cs = comps_of.get(m, ())
            hit = False
            stem = None
            for c in cs:
                if c.get("role") == "prefix" and c.get("word") == root:
                    hit = True
                elif c.get("role") == "stem":
                    stem = c.get("word")
            if not hit or not stem or stem == m or stem == root:
                continue
            sf = fam_of.get(stem)
            if sf is None or sf == root:
                continue
            if MIN_FAMILY_RANK.get(sf, BIG) <= root_rank:
                continue
            members.remove(m)
            families[sf].append(m)
            fam_of[m] = sf
            rehomed += 1

    # Sorted, and for the same reason as the re-homing loop above: this
    # pass also rewrites families as it goes, so iterating in dict order
    # made its decisions depend on PYTHONHASHSEED. It does not currently
    # fire on this deck (no family reaches the two-stems threshold), but
    # it is the same hazard and would reintroduce the drift the moment
    # the data changed. Sorted iteration costs nothing.
    detached = 0
    for root in sorted(families):
        members = families[root]
        if len(members) < 2 or root not in members:
            continue
        stems = set()
        for m in members:
            if m == root:
                continue
            cs = comps_of.get(m, ())
            is_pref = False
            st = None
            for c in cs:
                if c.get("role") == "prefix" and c.get("word") == root:
                    is_pref = True
                elif c.get("role") == "stem":
                    st = c.get("word")
            if is_pref and st:
                stems.add(st)
        if len(stems) < 2 or len(stems) * 2 < len(members):
            continue
        # Every non-root member must go somewhere: re-home each to the
        # family of the stem it is actually built on. Discarding them would
        # silently delete the word from the deck (the me bucket alone held
        # mjaft, menjëherë, meqë and five more).
        for m in list(members):
            if m == root:
                continue
            st = None
            for c in comps_of.get(m, ()):
                if c.get("role") == "stem":
                    st = c.get("word")
            # No stem means this member is not a prefix-compound at all
            # (vënë has no components; mjaftoj carries only the prefix
            # mjaft). Truncating the family would delete it, so keep it here.
            if not st:
                continue
            sf = fam_of.get(st)
            if sf is None or sf == root:
                continue
            if m not in families[sf]:
                families[sf].append(m)
            fam_of[m] = sf
        # Keep the root plus anything that could not be re-homed, so no
        # word is ever lost by detaching a bucket.
        keep = [root] + [m for m in members
                        if m != root and fam_of.get(m) == root]
        families[root] = keep
        fam_of[root] = root
        detached += 1

    for root, members in families.items():
        for m in members:
            by_word[m]["family"] = root
    if rehomed or detached:
        print("  function-word rescue: %d re-homed, %d detached"
              % (rehomed, detached))

    print("assigning levels...", flush=True)
    levels = schedule_course(cards, families,
                             components=by_word_components(cards),
                             opening=opening_levels.LEVELS)
    n_main = sum(1 for l in levels if not l[7].get("extended"))
    print("  %d levels: %d main course (rank <= %d), %d extended"
          % (len(levels), n_main, MAIN_MAX_RANK, len(levels) - n_main))

    level_objs = write_levels(levels, by_word, corpus_examples)

    top = cards[:30]
    report = {
        "stats": dict(stats),
        "families": len(families),
        "families_multi": len(multi),
        "levels": len(level_objs),
        "main_levels": sum(1 for l in level_objs if not l.get("extended")),
        "words": sum(l["word_count"] for l in level_objs),
        "pos": dict(Counter(p for c in cards for p in [s["pos"] for s in c["senses"]])),
        "etymology_class": dict(Counter(str(c["etymology_class"]) for c in cards)),
        "source_lang": dict(Counter(str(c["source_lang"]) for c in cards)),
        # Example sentences the orthography gate turned away, by source.
        "orthography_rejected": dict(sorted(Counter(r[0] for r in ORTHO_REJECTED).items())),
        "words_missing_etymology": sum(1 for c in cards if not c["etymology"]),
        "words_multi_pos": sum(1 for c in cards if len({s["pos"] for s in c["senses"]}) > 1),
        "largest_families": sorted(
            [{"root": r, "n": len(m)} for r, m in families.items() if len(m) > 1],
            # Ties broken by root: family order is hash-seed dependent, and
            # CI compares a rebuild to the committed data byte for byte.
            key=lambda d: (-d["n"], d["root"]))[:15],
        "sample_first_30": [{"sq": c["word"],
                             "pos": "/".join(sorted({s["pos"] for s in c["senses"]})),
                             "en": " | ".join(s["gloss"] for s in c["senses"][:2])}
                            for c in top],
    }
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    print("\nWrote data/course.json, data/index.json, data/report.json")
    print("Wrote data/levels/level_01..%0*d.json"
          % (max(2, len(str(len(level_objs)))), len(level_objs)))
    print("First 12 levels (root, gloss, words):")
    for l in level_objs[:12]:
        print("  %2d  %-12s %-34s %d words" % (l["level"], l["title"],
                                                l["root_gloss"][:34], l["word_count"]))
    split = [l for l in level_objs if l["parts"] > 1]
    if split:
        print("\n%d level(s) are a continuation of a large family:" % len(split))
        for l in split:
            print("  %s (%d/%d) %d words" % (l["root"], l["part"], l["parts"],
                                              l["word_count"]))
    print("\nMost frequent words in the deck:")
    for s in report["sample_first_30"][:15]:
        print("  %-10s %-14s %s" % (s["sq"], s["pos"], s["en"][:44]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
