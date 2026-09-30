#!/usr/bin/env python3
"""Form-of senses: which of them earn a card of their own?

'sense_is_content' in build_course.py drops every sense tagged form-of, on the
reasoning that an inflected form is already covered by its lemma's inflection
table. That is right for a dictionary and wrong for a course. In Albanian the
learner meets 'eshte' and 'jane' as words, and 'eshte' is rank 6 in the
frequency list while being absent from the deck. Measured with
tools/measure_form_gap.py: 3,250 high-frequency entries, 116 inside the top 500,
were being dropped.

The glosses themselves are usable ('third-person singular present indicative of
jam'), so the fix is to admit them rather than invent text. Three classes are
still rejected:

  * spelling variants ('eshte', 'isht') - the course is not a spelling drill,
    and the deck already carries the standard form.
  * bare noun/number inflection pointers ('inflection of zot:', 'plural of
    njeri') - these carry no meaning, only a pointer, so the card would read
    like a dictionary cross-reference. Note this does NOT drop the word from
    the deck: 'njeri' still teaches 'njerëz' in its own senses. It only means
    'njerëz' gets no card of its own under this rule.
  * a form-of sense on a word that is already a full entry in another part of
    speech. 'dhe' is the conjunction 'and' (rank 12) and the noun 'earth'; its
    aorist of 'jap' ('to give') is a different, minor word. Admitting it would
    file the conjunction under a verb lemma and teach the wrong thing, so a
    form-of sense is only ever used when the word has NO other content sense.
"""
import re

# A form-of gloss names a grammatical slot: person, number, tense, mood, case,
# gender, definiteness, or participial. Requiring a slot is what separates a
# real form ('third-person singular present indicative of jam') from a bare
# pointer ('inflection of zot:').
GRAMMAR_SLOT = re.compile(
    r"\b("
    r"indicative|subjunctive|jussive|conditional|imperative|infinitival|"
    r"present|past|future|imperfect|perfect|pluperfect|aorist|"
    r"first-person|second-person|third-person|"
    r"singular|plural|dual|"
    r"nominative|accusative|genitive|dative|ablative|locative|vocative|"
    r"masculine|feminine|neuter|"
    r"definite|indefinite|"
    r"participle"
    r")\b",
    re.I,
)

# The lemma name sits after the last 'of' that introduces it. Glosses vary:
#   '...indicative of jam'
#   '...indicative of dua; "I wanted", "I loved"'   <- trailing gloss survives
#   'accusative of ti, you (singular)'              <- trailing gloss survives
#   'past participle of vij ("to arrive")'         <- parenthesised gloss
#   '...indicative of marr ((you) take)'            <- parenthesised gloss
# So split the lemma off first, then test the remainder for a trailing gloss.
# Parentheses matter as much as punctuation: 'marr ((you) take)' is a good
# lemma, and rejecting it for the parenthesis loses verbs like merr and mora.
# (no count arg here: this is used with re.split, which takes the count)
_SPLIT_TRAILING = re.compile(r"[\[,;:]|\s*\(")
# 'ky and kjo' is a two-word lemma reference, not a single name.
_LEMMA_NAME = re.compile(r"^[A-Za-zëçËÇ][A-Za-zëçËÇ' -]*$")

MISSPELLING = re.compile(r"\bmisspell", re.I)


def _lemma_candidates(remainder):
    """Word groups in the text after the final 'of'."""
    # A gloss already rewritten by form_gloss names its lemma mid-parenthetical,
    # as in 'he/she/it (subjunctive) say (from them, to say)'. Taking the text
    # after the final 'of' there yields 'say)', which is not a lemma, so that
    # shape is read first and directly.
    fm = re.search(r"\(from\s+([A-Za-zëçËÇ][A-Za-zëçËÇ'-]*)\s*,", remainder or "")
    if fm and re.match(r"^[A-Za-zëçËÇ][A-Za-zëçËÇ'-]*$", fm.group(1)):
        return [fm.group(1)]

    m = re.search(r"\bof\b(.*)$", remainder, re.I)
    if not m:
        return []
    tail = m.group(1).strip()
    # A trailing gloss is separated from the lemma by a comma, semicolon or
    # colon. Keep only the part before it.
    cut = _SPLIT_TRAILING.split(tail)[0].strip()
    if not cut:
        return []
    # 'ky and kjo' -> keep the leading name; it is the canonical one.
    cut = re.split(r"\band\b", cut)[0].strip()
    if not _LEMMA_NAME.match(cut):
        return []
    return [cut]


def form_of_lemma(gloss, tags=None, words=None):
    """Return the lemma a form-of gloss points at, or None to reject the sense.

    'words' is the set of lemma names the deck knows; a form-of gloss pointing
    at something outside it is rejected rather than creating a dangling link.
    """
    if not gloss:
        return None
    g = str(gloss).strip()
    tags = list(tags or [])

    if MISSPELLING.search(g):
        return None
    # Spelling/dialect variants are not vocabulary.
    if any(re.search(r"\balternative\b", str(t), re.I) for t in tags):
        return None
    # A slot must be named, else this is a bare pointer ('inflection of zot:').
    if not GRAMMAR_SLOT.search(g):
        return None

    lemmas = _lemma_candidates(g)
    if not lemmas:
        return None
    lemma = lemmas[0]
    if words is not None and lemma not in words:
        return None
    return lemma
