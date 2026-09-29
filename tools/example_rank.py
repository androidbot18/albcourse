"""Example ranking for the Albanian course.

The learner asked for example sentences that are short, memorable, and built
from vocabulary introduced in the same lesson or an earlier one. Wiktionary
offers several sentences for some words and none at all for most, so choosing
which example ships is a real decision worth making well.

Ranking lives here, at build time, because the deck-wide frequency table only
exists during the build. The browser cannot rank: it has one card at a time and
no view of which other words the learner has already met.

Design rule, learned the hard way: RANKING MUST NEVER REDUCE COVERAGE. A first
version hard-rejected any example that did not literally contain the headword
token, and that silently cost 149 cards their only example - including good
ones like "Eshte e bukur." for jam and "Une di. Une s'di." for se. Rejecting is
the wrong tool: the source is so thin (examples for only ~955 Albanian
headwords) that losing even one card is a real loss to the learner. So the
headword test is a strong BONUS, not a gate, and only unusable text is dropped.

Signals, in order of weight:

  1. a real sentence at all: Albanian text plus an English translation.
     This is the only hard gate.
  2. the headword should appear, ideally as a whole token. Inflected forms and
     clitics still count via a prefix match, because Albanian is heavily
     suffixed.
  3. length. Three to nine tokens is the memorable band. A sentence needs a
     verb or a full noun phrase to teach anything, so a bare two-word fragment
     such as "libri im" scores below a proper sentence even though it is short.
     Fragments are not dropped, only outranked.
  4. familiarity of the surrounding words: corpus rank at or before this
     word's own rank means the learner has already met it. Rare filler forces a
     dictionary lookup, which defeats the purpose.

A hard limit worth stating plainly: Wiktionary holds examples for only about
955 Albanian headwords, so most of the 3,731 cards have none to choose from.
That is a limit of the source, and it is deliberately NOT patched over with
invented sentences.
"""

import re

# Word characters, excluding digits and underscore, Unicode-aware so E-e,
# C-c and friends tokenize as letters.
_TOKENS = re.compile(r"[^\W\d_]+", re.UNICODE)

# The memorable band. Outside it a sentence is still usable, just weaker.
_SHORT, _LONG = 3, 9

# Frequent function words whose only role in a sentence is to carry a suffix.
# Looking them up bare would mark a conjugated common word as rare.
_UNINFLECT = {
    "eshte": "eshte", "jam": "jam", "jane": "jam", "je": "jam",
    "is": "jam", "jan": "jam", "ishte": "eshte",
    "kam": "kam", "ka": "kam", "kemi": "kam", "keni": "kam",
    "kish": "kam", "kishte": "kam", "kane": "kam",
    "ky": "ky", "kjo": "ky", "keto": "ky", "keta": "ky",
    "ai": "ai", "ajo": "ai", "ata": "ai", "ato": "ai", "as": "ai",
    "une": "une", "ne": "ne", "ju": "ju", "ti": "ti",
    "e": "e", "i": "i", "te": "te", "ne": "ne", "me": "me",
    "nuk": "nuk", "po": "po", "dhe": "dhe", "ose": "ose",
    "gjithe": "gjithe", "shume": "shume", "pak": "pak", "mire": "mire",
    "ketu": "ketu", "aty": "aty", "tani": "tani", "pastaj": "pastaj",
    "gjithashtu": "gjithashtu", "vetem": "vetem", "se": "se",
    "qe": "qe", "si": "si", "ku": "ku", "sa": "sa", "ma": "ma",
    "edhe": "edhe", "vete": "vete", "keshtu": "keshtu", "ashtu": "ashtu",
    "para": "para", "pas": "pas", "mbi": "mbi", "nen": "nen",
    "deri": "deri", "prej": "prej", "nga": "nga", "te": "te",
    "pa": "pa", "per": "per", "rreth": "rreth", "ndaj": "ndaj",
    "qe": "qe", "sepse": "sepse", "megjithese": "megjithese",
    "prind": "prind", "lart": "lart", "poshte": "poshte",
    "brenda": "brenda", "jashte": "jashte", "an": "an",
    "gjith": "gjith", "sa": "sa", "qe": "qe",
}


def tokenize(text):
    """Lower-cased word tokens of an Albanian sentence."""
    return [t.lower() for t in _TOKENS.findall(text or "")]


def contains_headword(text, headword):
    """Does this sentence actually use the word it is illustrating?

    Whole-token match first. Then a prefix match, because Albanian attaches
    suffixes aggressively: "shqip" is the head of "shqipe", and function words
    appear as clitics ("s'e"). A prefix match alone would wrongly accept an
    unrelated word that merely starts the same way, so the whole-token pass
    runs first and only then do we fall back to prefixes.
    """
    head = (headword or "").lower()
    if not head:
        return False
    tokens = tokenize(text)
    if head in tokens:
        return True
    return any(t.startswith(head) or head.startswith(t) for t in tokens if t)


def _familiarity(tokens, headword, own_rank, freq):
    """Fraction of the non-headword tokens the learner has already met."""
    head = (headword or "").lower()
    others = [t for t in tokens if t != head]
    if not others:
        return 0.0
    known = 0
    for token in others:
        entry = freq.get(token)
        if entry is None:
            entry = freq.get(_UNINFLECT.get(token))
        if entry is not None and entry[0] <= own_rank:
            known += 1
    return known / len(others)


def score_example(example, headword, own_rank, freq):
    """Score one example. Higher is better.

    Returns 0 only for text that is unusable as an example: no Albanian, or no
    English to check it against. Every other example keeps a positive score, so
    ranking can reorder but never delete.

    example: dict with "sq" (Albanian) and "en" (English translation).
    headword: the Albanian word being taught.
    own_rank: that word's corpus rank, so "already met" is well defined.
    freq: dict mapping a word to its (rank, count) entry.
    """
    text = (example.get("sq") or "").strip()
    translation = (example.get("en") or "").strip()
    # The single hard gate. Everything else is a preference.
    if not text or not translation:
        return 0

    tokens = tokenize(text)
    if not tokens:
        return 0

    score = 100.0

    # A sentence that never says the word it illustrates is a poor example, but
    # still better than none - hence a bonus rather than a rejection.
    if contains_headword(text, headword):
        score += 40.0

    # Length, with a floor for the useful minimum.
    n = len(tokens)
    if _SHORT <= n <= _LONG:
        score += 30.0
    elif n < _SHORT:
        # Too short to be a sentence. Penalise, never drop.
        score += 12.0 * n
    else:
        score += max(0.0, 30.0 - (n - _LONG) * 2.0)

    # Familiarity of the surrounding words. The headword is expected to be new,
    # so it is excluded rather than counted as a miss.
    score += round(25.0 * _familiarity(tokens, headword, own_rank, freq), 2)

    return score


def rank_examples(examples, headword, own_rank, freq):
    """Return every example ordered best-first. None are dropped.

    Ties break on the shorter sentence and then alphabetically, so repeated
    builds produce byte-identical output.
    """
    scored = []
    for example in examples:
        score = score_example(example, headword, own_rank, freq)
        text = example.get("sq") or ""
        scored.append((score, len(text), text, example))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [item[3] for item in scored]
