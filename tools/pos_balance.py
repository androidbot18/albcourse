# Which cards a learner meets in the opening levels.
#
# Item 4. Measured: only 3 of the 100 most frequent words have a noun as
# their headline sense, and levels 1-10 are 9% noun, 55% verb. That is the
# wrong first contact with a language.
#
# The first version of this rule promoted 138 cards and hit 71% nouns, and
# promoted `eshtë` ("fiber"), `sheh` ("head of a religious group") and
# `bej` ("lord in feudalism") into the first sessions. Those are not wrong
# data -- each really is a noun-led card -- they are simply not words a
# beginner can act on. A word is only worth an early slot if it is common,
# concrete, AND a plain everyday noun rather than a specialist, archaic or
# cultural one.

EARLY_LEVELS = 10
TARGET_NOUN_SHARE = 0.30
MAX_RANK = 2000

# Specialist, taxonomic or scientific registers. A bird is a thing; a family
# of passerines is a taxonomy lesson.
# Abstract or nominalized nouns. Grammatical rather than lexical: they are
# a word turned into a noun ("still" -> "stillness", "past" -> "the past"),
# not a thing. A learner meets those in context, not in a noun lesson.
ABSTRACT = (
    'still', 'past', 'event, occurrence', 'age', 'great desire', 'lust',
    'envy', 'sort, kind, type', 'scale (of fish)', 'incense',
    'lady in a wealthy', 'fool, crazy', 'joke, prank', 'nail (of the body)',
)

SPECIALIST = (
    'zoolog', 'botan', 'geolog', 'mineralog', 'anatom', 'physiol', 'muscle fiber',
    'mathemat', 'meteorolog', 'geograph', 'technolog', 'architectur',
    'jurisprud', 'grammatical', 'linguistic', 'mytholog', 'theolog', 'ferment',
    'philosophic', 'entomolog', 'ornitholog', 'ichthyolog', 'taxonomic',
    'class ', 'subclass', 'order ', 'family of', 'genus', 'species', 'genus',
    'unit of', 'measure of', 'currency', 'herbivorous', 'perennial',
    'deciduous', 'fagus', 'sylvatica', 'larva', 'metamorph',
)

# Archaic, feudal, religious or purely cultural registers. These are real
# Albanian words, and a learner will meet them eventually, but they teach
# nothing about how to use the language in a first session.
CULTURAL = (
    'feudal', 'nobility', 'bey', 'sheik', 'pasha', 'sultan', 'lord',
    'province', 'ruler', 'title of', 'respectful title', 'ottoman',
    'religious group', 'clergy', 'imam', 'dervish', 'saint', 'shrine',
    'ancient roman', 'byzantine', 'medieval', 'ancient greek', 'latin',
    'used in names', 'surname', 'given name', 'surname',
)


def headline_pos(card):
    """The POS of the sense the card actually teaches, or None.

    Accepts both card shapes in this repo. A build-time card (from
    build_course.py) keys the headword `word` and holds senses under `senses`;
    a shipped card (level files / words.json) uses `sq` and `sense_detail`.
    The first attempt at the early-noun rule read only `sense_detail`, which
    is absent from every build-time card, so it silently found no nouns and
    promoted nothing.
    """
    sd = card.get('sense_detail')
    if not sd:
        sd = card.get('senses') or []
    if not sd:
        return None
    return sd[0].get('pos')


def gloss(card):
    """The card's headline English gloss, whichever shape it arrived in."""
    g = card.get('en')
    if not g:
        sd = card.get('sense_detail') or card.get('senses') or []
        g = sd[0].get('gloss') if sd else ''
    return (g or '').lower()


def is_pictureable_noun(card):
    'True when the headline is a common, concrete, everyday noun.'
    if headline_pos(card) != 'noun':
        return False
    g = gloss(card)
    for marker in SPECIALIST + CULTURAL + ABSTRACT:
        if marker in g:
            return False
    return True


def is_form_of_other(card):
    'True for a noun that is only an inflected form of another word.'
    g = gloss(card)
    if g.startswith('the ') and ('singular' in g or 'plural' in g):
        return True
    return False


def promote(card, level, family_size):
    'Should this card be pulled into the opening levels?'
    if level is not None and level <= EARLY_LEVELS:
        return False
    if not is_pictureable_noun(card):
        return False
    if is_form_of_other(card):
        return False
    if family_size > 1:
        return False
    if card.get('rank', 10 ** 9) > MAX_RANK:
        return False
    return True


def quota(current_words, current_nouns):
    """How many more nouns the early window may take before it hits target.

    The first version promoted every card the rule liked: 138 promotions
    and a 71% noun opening. The target is a share, not a maximum -- once the
    window holds enough nouns the rule stops firing even when more eligible
    words exist. That is the difference between rebalancing the opening and
    replacing it.
    """
    have = current_words + current_nouns
    want = int(round(TARGET_NOUN_SHARE * have / (1.0 - TARGET_NOUN_SHARE)))
    return max(0, want - current_nouns)


# How much vocabulary the opening window spans, in WORDS rather than
# families.
#
# It used to be a fixed 20 families, which only held while the opening was
# dominated by very large families (jam alone had 21 members, so 20
# families covered 158 words). Teaching the common function words early
# re-homes compounds to their stem families, which makes the opening
# families smaller -- the same 20 families then held 96 words, and the
# noun rebalance lost its footing without failing loudly.
#
# Measured in words it states the actual intent: cover the first ten
# levels, whatever shape the families happen to be.
WINDOW_WORDS = 90


def spread(chosen, natural):
    """Assign each chosen family a synthetic rank that interleaves it into
    `natural` (family roots already in frequency order).

    The topological sort in build_course.py orders by (score, root), so a
    promotion has to be expressed as a score to take effect. Setting score=0
    does not interleave: it displaces every other family, which is what
    produced an 88.8%-noun opening with `te` and `nuk` demoted to level 9.

    Each chosen family instead gets a fractional rank strictly between its
    natural neighbours, so the nouns land at their target slot and everything
    else keeps its place. Fractional ranks are fine -- the value only has to
    sort correctly.

    Returns {root: synthetic_rank}.
    """
    if not chosen:
        return {}
    cset = set(chosen)
    pool = [r for r in natural if r not in cset]
    if not pool:
        return {r: 0.0 for r in chosen}

    # Slots in the merged sequence: walk the pool and decide, before each
    # pool item, whether a chosen noun is due. `due` is a counter of nouns
    # still to place; the share test is the same one quota() uses.
    total = len(pool) + len(chosen)
    out = {}
    ci = 0
    step = 1.0 / (len(pool) + 1.0)
    for i, r in enumerate(pool):
        # Want this many nouns among the slots emitted so far (including the
        # one about to be emitted).
        slots = i + 1
        want = TARGET_NOUN_SHARE * (slots + len(out))
        while ci < len(chosen) and len(out) < want:
            # Slot just before pool item i: (i - 1) + small offset.
            out[chosen[ci]] = (i - 1) + step * (ci + 1)
            ci += 1
    # Any chosen nouns left over (the target was not reached because the pool
    # ran out) go at the end, in order, without colliding.
    tail = len(pool) - 1
    while ci < len(chosen):
        out[chosen[ci]] = tail + step * (ci + 1)
        ci += 1
    return out
