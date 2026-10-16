"""Orthography gate for example sentences.

An Albanian course should never show misspelt Albanian, and the two example
sources both carry some:

- Wiktionary quotes historical texts (Buzuku, Budi, Bogdani) in their own
  pre-standard spelling: "CHeio anſte ieta e ameſuome", "e ћi iane teh
  beћate". Valuable to a philologist, unreadable to a learner.
- Subtitle-aligned corpus sentences are often typed without `ë`, or with a
  Lithuanian `ė` in its place: "Ai eshte ...", "Pa fitore, nuk do tė ketė
  paqė.", "Me afer, bir."

Two checks, both cheap enough to run on every candidate sentence:

1. Alphabet. Every letter must be in the Albanian alphabet (a-z without w,
   plus ë and ç). This rejects historical spelling, `ė`, Greek and Cyrillic
   script, accented loans (Beyoncé) and English text that leaked into the
   Albanian side.
2. Missing ë. A token without ë is a misspelling when the dictionary does not
   know it as a word and a spelling with ë in place of one or more e's is a
   dictionary word that the corpus uses at least SPELLING_RATIO times as
   often. `eshte` (rank 70) vs `është` (rank 6) is caught. `te`, `ne` and
   `qe` are real words and pass. So do `veten` and `merre`, which the
   dictionary's form tables happen to miss but the corpus ranks well above
   their ë-spelling.

Rejecting costs coverage, which example_rank.py otherwise guards closely.
Here the trade is deliberate: a card with no example is a gap, but a card
with a misspelt example teaches the misspelling.
"""
import re

# Albanian alphabet letters. `w` is not one; it only appears in foreign names.
ALBANIAN_LETTERS = frozenset("abcçdeëfghijklmnopqrstuvxyz"
                             "ABCÇDEËFGHIJKLMNOPQRSTUVXYZ")

_TOKENS = re.compile(r"[^\W\d_]+", re.UNICODE)

# How much more frequent the ë-spelling must be before the bare spelling
# counts as a typo. 4 catches ketu/këtu (234 vs 38) and ben/bën (505 vs
# 105), and leaves merre/merrë (345 vs 5310) alone.
SPELLING_RATIO = 4

# Real words that the dictionary's form tables miss and whose ë-spelling
# happens to be more frequent. Reviewed by hand.
KNOWN_WORDS = frozenset({
    "banje",  # ablative/genitive of banjë: "rroba banje", swimwear
})

# The most frequent ë-less typos, so the gate does not depend on the
# dictionary for these.
COMMON_TYPOS = frozenset({
    "eshte", "nje", "per", "mire", "gje", "ben", "ketu", "vetem", "shume",
    "une", "jane", "kete", "keto", "keshtu", "gjithe", "asgje", "jete",
})


def foreign_letters(text):
    """Letters in text that are not in the Albanian alphabet."""
    return sorted({ch for ch in text if ch.isalpha() and ch not in ALBANIAN_LETTERS})


def _e_variants(token):
    """Spellings of token with ë in place of one or more of its first 5 e's."""
    idx = [i for i, ch in enumerate(token) if ch == "e"][:5]
    for mask in range(1, 1 << len(idx)):
        chars = list(token)
        for bit, i in enumerate(idx):
            if mask >> bit & 1:
                chars[i] = "ë"
        yield "".join(chars)


class Gate:
    """The gate, bound to the dictionary's word set and the corpus ranking.

    known: lower-cased words and inflected forms the dictionary lists.
    rank:  word -> corpus frequency rank (1 is most frequent).
    """

    def __init__(self, known, rank):
        self.known = known
        self.rank = rank
        self._cache = {}

    def misspelling(self, token):
        """The ë-spelling token should have had, or None if token is fine."""
        t = token.lower()
        if t in self._cache:
            return self._cache[t]
        fix = None
        if "ë" not in t and "e" in t and t not in KNOWN_WORDS:
            # The most frequent dictionary word among the ë-spellings.
            cands = [(self.rank.get(v, 10 ** 7), v) for v in _e_variants(t)
                     if v in self.known]
            best = min(cands) if cands else None
            if t in COMMON_TYPOS:
                fix = best[1] if best else t
            elif t not in self.known and best and \
                    best[0] * SPELLING_RATIO < self.rank.get(t, 10 ** 7):
                fix = best[1]
        self._cache[t] = fix
        return fix

    def problems(self, sq, headword=None):
        """Why sq fails the gate, as a list of short strings (empty: it passes).

        The card's own headword is never counted as a misspelling: a form
        card such as `rrime` must be allowed to show itself.
        """
        out = ["letter %s" % ch for ch in foreign_letters(sq)]
        head = (headword or "").lower()
        for tok in _TOKENS.findall(sq):
            if tok.lower() == head:
                continue
            fix = self.misspelling(tok)
            if fix:
                out.append("%s for %s" % (tok, fix))
        return out

    def ok(self, sq, headword=None):
        return not self.problems(sq, headword)


def known_words(entries):
    """The dictionary's lower-cased headwords and inflected forms."""
    known = set()
    for e in entries:
        w = e.get("word")
        if w:
            known.add(w.lower())
        for f in e.get("forms") or []:
            for t in _TOKENS.findall(str(f.get("form") or "").lower()):
                known.add(t)
    return known
