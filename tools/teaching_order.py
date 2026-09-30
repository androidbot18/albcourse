"""Teaching priority: which cards of a word family a learner should meet first.

A family is atomic in the level builder, so a 21-member verb family like `jam`
eats three whole sessions before the learner sees a single concrete noun. The
cards are correct; the order is not. Nothing here removes a word from the
course -- it only decides what sorts to the front of its own family.

Tier 0 must-learn: the lemma and its common present-tense forms.
Tier 1 useful: other finite forms -- perfect, imperfect, subjunctive, imperative.
Tier 2 defer: archaic, dialectal and literary survivals.

The signal is the English gloss, because that is the only place the tense and
the register are recorded. The form-gloss pass rewrote `ishte` to "he/she/it
(used to) was", so the tense is recoverable without re-parsing Wiktionary tags.

A card passed to teaching_tier() is a build-time card, so the gloss lives in
card["senses"][0]["gloss"], NOT in card["gloss"]. Accepting either keeps this
callable from the level tests, which construct minimal dicts.
"""

ARCHAIC = (
    "archaic", "dialectal", "literary", "obsolete", "poetic", "rare",
    "regional", "dated", "nonstandard",
)

# Finite forms a learner needs before anything else in a verb family.
CORE_PRESENT = (
    "he/she/it is", "they are", "i am", "you are", "we are",
    "he/she/it are", "i'm", "to be",
)

# Real Albanian grammatical forms, taught after the present paradigm.
OTHER_FINITE = (
    "(used to) was", "(used to) were", "(have done)", "(has done)",
    "would", "subjunctive", "conditional", "imperative", "participle",
    "gerund", "indicative", "optative",
)


def card_gloss(card):
    """The card's headline English gloss, whichever shape the caller used."""
    if not isinstance(card, dict):
        return ""
    g = card.get("gloss")
    if isinstance(g, str) and g.strip():
        return g
    senses = card.get("senses") or []
    if senses and isinstance(senses[0], dict):
        return senses[0].get("gloss") or ""
    return ""


def teaching_tier(card):
    """0 = must learn early, 1 = useful, 2 = defer as long as possible."""
    gloss = card_gloss(card).lower()
    head = gloss.split(";")[0].strip()

    for marker in ARCHAIC:
        if marker in gloss:
            return 2
    for marker in OTHER_FINITE:
        if marker in head:
            return 1
    for marker in CORE_PRESENT:
        if head.startswith(marker):
            return 0
    return 0


def tier_of_word(cards_by_word, word):
    """teaching_tier for `word` given a {word: card} mapping."""
    return teaching_tier(cards_by_word.get(word) or {})
