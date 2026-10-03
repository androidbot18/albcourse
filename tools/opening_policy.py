"""What is allowed to teach in the opening levels, and what waits.

The opening was curated by frequency alone, and the frequency list is
OpenSubtitles. Of the 45 most frequent tokens exactly one is a plain
content noun (zemer); the rest are conjunctions, pronouns, clitics and
inflected verb forms. Ranking by frequency and taking the top therefore
produces a wall of grammatical scaffolding BY CONSTRUCTION, so no POS
filter fixes a list shaped that way.

Measured on the shipped opening (levels 1-10, 66 cards):

    te(1) ne(3)                    conjunctions, level 1
    do(4) + domethene(1628) ndopak(8499) domosdoshem(20233)
    domosdoshmerisht(22083) medoemos(22302) doemos(30516)
    domosdoshmeri(38595)          one rank-4 word, six rank-8500+ words
    jam: 22 members, levels 3, 4 and 5
    nje: 8 members, level 8

"""



# Closed-class grammatical words, by the short POS tag this repo uses
# (see build_course.CORE_POS). Pronouns and verbs are deliberately NOT
# listed: pronouns are rare enough to survive the family cap, and verbs
# are the conjugations the brief keeps.
FUNCTION_POS = frozenset({"conj", "prep", "det", "num"})


# Which closed-class words may keep a slot in the opening levels.
#
# This started as a plain count and was wrong. Budgeting by frequency
# admitted the six most frequent closed-class roots -- te, ne, do, me, qe,
# nje, all inside rank 1-11 -- which are precisely the words that made
# level 1 a wall of grammar. A count cannot fix that: the most frequent
# function words are the most grammar-shaped, not the most useful.
#
# So the opening admits a named set. These are the words a learner needs
# before they can build a sentence, and each is a plain piece of everyday
# syntax rather than a subjunctive marker or a clitic:
#
#   dhe and     nje one se  that/as/than
#   me  with    per for      ne  in/at
#
# Everything else closed-class is deferred -- taught later, never dropped.
# `te` (rank 1), `qe` (rank 10), `do` (rank 4) and the clitic `me` are the
# most visible exclusions, and they are the right ones: they mark the
# subjunctive and attach to the verb, which is grammar work rather than
# first-week vocabulary.
OPENING_FUNCTION_WORDS = frozenset({
    "dhe", "një", "se", "me", "për", "në",
})


# Words whose FAMILY stays in the opening, named because deferring the word
# pushed its rare tail into the opening instead of out of it.
#
# `nje` and `me` are the two cases. Both are admitted above, but the gate
# still pushed their families back, and a family cannot be split by this
# policy -- so the tail came forward to fill the slot the head vacated:
# njezet, njesi, njembedhjete and menjane filled level 9, and mjaftoj
# (rank 42540) reached level 10. Deferring a function word whose family
# carries a rank-42540 tail makes the opening worse, not better, so the
# family is admitted whole.
OPENING_FUNCTION_FAMILIES = frozenset({
    "një", "me",
})


# Size of that set, so the builder and this module cannot drift apart.
MAX_FUNCTION_WORDS = len(OPENING_FUNCTION_WORDS)


# A derived form may only ride its stem family into the opening if it is
# itself reasonably common.
#
# This mirrors build_course.OPENING_MEMBER_MAX_RANK (1200), which encodes
# the same ceiling for the family split. It is restated rather than
# imported because build_course imports THIS module: importing the
# constant back would be a circular import. The test in
# test_opening_policy.py pins the two values equal so they cannot drift.
MAX_TAIL_RANK = 1200


# How many levels count as the opening. Mirrors pos_balance.EARLY_LEVELS,
# restated for the same reason as MAX_TAIL_RANK: build_course imports this
# module, so importing back would be circular. test_opening_policy.py pins
# the two values equal.
EARLY_LEVELS_DEFAULT = 10


# The three card shapes in this repo carry the POS of a word under two
# different vocabularies, and the mismatch is silent:
#
#   words.json   .pos            -> full words: 'conjunction', 'preposition'
#   level_*.json sense_detail[] -> short tags: 'conj', 'prep'
#   build-time   senses[0].pos  -> short tags: 'conj', 'prep'
#
# FUNCTION_POS is written in the SHORT namespace, so a lookup that only
# accepts short tags returns None for every shipped card and the gate
# silently matches nothing. That is the failure pos_balance hit before it,
# and it is why headline_pos() normalises.
POS_FULL_TO_SHORT = {
    "noun": "noun", "verb": "verb", "adj": "adj", "adjective": "adj",
    "adv": "adv", "adverb": "adv", "pron": "pron", "pronoun": "pron",
    "num": "num", "numeral": "num", "intj": "intj",
    "interjection": "intj", "prep": "prep", "preposition": "prep",
    "conj": "conj", "conjunction": "conj", "det": "det",
    "determiner": "det",
}


def _norm_pos(p):
    """One POS string from either namespace, or None if unknown."""
    if not isinstance(p, str):
        return None
    return POS_FULL_TO_SHORT.get(p.strip().lower())


def headline_pos(card):
    """The POS of the sense the card teaches, normalised, or None.

    Handles all three shapes and both vocabularies, so these gates work on
    build-time cards and on shipped level/index cards alike.
    """
    if not isinstance(card, dict):
        return None
    sd = card.get("sense_detail") or card.get("senses") or []
    if sd and isinstance(sd, list) and isinstance(sd[0], dict):
        p = _norm_pos(sd[0].get("pos"))
        if p:
            return p
    flat = card.get("pos")
    if isinstance(flat, list):
        for raw in flat:
            p = _norm_pos(raw)
            if p:
                return p
    return None


def is_function_word(card):
    """True when this card teaches closed-class scaffolding."""
    return headline_pos(card) in FUNCTION_POS


def is_rare_tail(card):
    """True when this card is too rare to ride its stem into the opening."""
    rank = card.get("rank")
    if not isinstance(rank, int):
        return False
    return rank > MAX_TAIL_RANK


def admits_family_to_opening(root):
    """May this family keep its whole self in the opening?

    A family is atomic, so deferring its head hands the opening slot to its
    rare tail instead. The two families where that trade is a loss are
    named in OPENING_FUNCTION_FAMILIES.
    """
    return root in OPENING_FUNCTION_FAMILIES


def admits_to_opening(word):
    """May this closed-class word keep a slot in the opening levels?

    True only for the named everyday set in OPENING_FUNCTION_WORDS. Every
    other conjunction, preposition, determiner and numeral is deferred --
    taught later, never dropped.
    """
    return word in OPENING_FUNCTION_WORDS


def function_word_budget():
    """How many function-word cards the opening may hold.

    A function so the constant has one home and builder and test cannot
    drift apart.
    """
    return MAX_FUNCTION_WORDS
