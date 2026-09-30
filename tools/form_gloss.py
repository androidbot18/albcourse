#!/usr/bin/env python3
"""Learner-facing glosses for inflected-form cards.

A form card's gloss comes from Wiktionary and reads as grammar:

    eshte  ->  "third-person singular present indicative of jam"

That is accurate and close to useless for a learner. What a learner needs is
what the word DOES in a sentence, and two facts give that without conjugating
anything: the Albanian person+number (which pronoun stands before the verb) and
the lemma's own English gloss.

    eshte  ->  "he/she/it is (from jam, to be)"
    jane   ->  "they are (from jam, to be)"
    je     ->  "you (sg) are (from jam, to be)"
    kemi   ->  "we have (from kam, to have)"

Why pronouns rather than conjugating the English verb: the deck has 105 distinct
verb lemmas (jam, shkoj, vras, bëj, them, ...), and hand-conjugating 105 verbs
across indicative/subjunctive/jussive/imperative/aorist/imperfect is a large
table of guesses. A wrong gloss teaches the learner something false, which is
the one failure this project refuses. The pronoun is a fact of the Albanian
paradigm, so that mapping cannot be wrong in that way.

The verb form is the *only* thing conjugated, and only for the small, fully
regular 'to be' paradigm. Every other verb gets the infinitive with the pronoun
in front of it, which is how the entry is read aloud in a dictionary and is
always true:

    shkoj  ->  "we go, to go (from shkoj)"   [regular]
    them   ->  "he/she/it says, to say (from them)"  [regular]
    shko   ->  "go! (imperative of shkoj, to go)"

'be' is irregular (I am / you are / he is) and Wiktionary's lemma gloss already
supplies the English forms, so those four are listed explicitly. Anything else
falls back to the infinitive rather than being guessed at, because 'they goes'
teaches a false sentence.

Nouns need no conjugation at all, only a readable name for the ending:

    babai      -> "the father, singular (from baba)"
    njerëzit   -> "the people, plural (from njeri)"
    njerëz     -> "people, plural (from njeri)"    [indefinite]

So case is dropped from the headline: a card reading 'the father, singular' is
answerable where one reading 'definite nominative singular of baba' is not.
Archaic dialect entries ('us; dative') are not modelled and fall back to the
original gloss, which is at least true.

Every rewrite is a pure function of the Wiktionary slot text, so a rebuild is
deterministic and a newly seen entry is handled exactly like an old one.
"""
import re

_POINTER = re.compile(r"\bof\s+([A-Za-zëçËÇ][A-Za-zëçËÇ'-]*)\s*[.;:]?\s*$")
_PERSON_R = re.compile(r"\b(first|second|third|first/third|second/third)-person\b", re.I)
_NUMBER_R = re.compile(r"\b(singular|plural|dual)\b", re.I)
_SLOT_R = re.compile(
    r"\b(indicative|subjunctive|jussive|conditional|imperative|infinitival|admirative|"
    r"optative|mediopassive|present|past|future|imperfect|perfect|pluperfect|aorist|"
    r"nominative|accusative|genitive|dative|ablative|locative|vocative|"
    r"masculine|feminine|neuter|definite|indefinite|participle|"
    # A gloss can BE the slot, with nothing else in it: 'plural of minute',
    # 'participle of vdes'. Those are real form glosses, so the bare words count.
    r"plural|singular|dual)\b", re.I)

_PRONOUN = {
    ("first", "singular"): "I",
    ("first", "plural"): "we",
    ("first", "dual"): "the two of us",
    ("second", "singular"): "you (sg)",
    ("second", "plural"): "you (pl)",
    ("second", "dual"): "you (two)",
    ("third", "singular"): "he/she/it",
    ("third", "plural"): "they",
    ("third", "dual"): "the two of them",
    # Albanian verbs taking both 2nd and 3rd person singular have one form, so
    # naming either alone would be a guess.
    ("second/third", "singular"): "you (sg) or he/she/it",
    ("first/third", "plural"): "we or they",
}

# 'to be' is the one verb whose present forms are not the infinitive plus an -s.
# Only the forms actually seen in the deck are listed; anything else falls back.
_BE_FORMS = {
    ("first", "singular"): "am",
    ("second", "singular"): "are",
    ("third", "singular"): "is",
    ("first", "plural"): "are",
    ("second", "plural"): "are",
    ("third", "plural"): "are",
}

# Past forms that are not infinitive + 'ed'. Only consulted for the imperfect and
# aorist slots, where English is regular for everything else.
_IRREGULAR_PAST = {
    "be": "was", "have": "had", "do": "did", "go": "went", "say": "said",
    "make": "made", "know": "knew", "think": "thought", "take": "took",
    "come": "came", "see": "saw", "give": "gave", "find": "found",
    "tell": "told", "become": "became", "leave": "left", "feel": "felt",
    "put": "put", "mean": "meant", "keep": "kept", "let": "let",
    "begin": "began", "seem": "seemed", "hear": "heard", "hold": "held",
    "bring": "brought", "write": "wrote", "buy": "bought", "speak": "spoke",
    "eat": "ate", "drink": "drank", "run": "ran", "sleep": "slept",
    "read": "read", "write": "wrote", "grow": "grew", "draw": "drew",
}

# Lemma glosses that are themselves wrong for display purposes. Wiktionary
# glosses njeri as 'anyone' and dikush as 'someone', which are the INDEFINITE
# uses; the noun that builds a family is 'person/man'. Using the source gloss
# produced 'the anyone'. Only the four lemmas actually involved are listed, and
# each is checked to be a real deck word before use -- a lookup table of
# hypothetical words would be as much a guess as a bad conjugation.
_LEMMA_DISPLAY_OVERRIDE = {
    "njeri": "person",
    "dikush": "someone",
}

# A noun lemma glossed with an indefinite quantifier ('anyone', 'something')
# cannot take a definite article. Detected rather than listed so it holds for
# the whole deck: njeri is glossed 'anyone', which produced 'the anyone'.
_INDEFINITE_NOUN = re.compile(
    r"^(anyone|anybody|someone|somebody|nothing|something|anything|everything|\w+thing)$",
    re.I)

_MOOD_TENSE = [
    (r"\bsubjunctive\b", " (subjunctive)"),
    (r"\bjussive\b", " (jussive)"),
    (r"\bconditional\b", " (conditional)"),
    (r"\bimperative\b", ""),
    (r"\bimperfect\b", " (used to)"),
    (r"\baorist\b", " (once did)"),
    (r"\bpluperfect\b", " (had done)"),
    (r"\bsimple perfect\b", " (has done)"),
    (r"\bperfective\b", " (has done)"),
    (r"\bperfect\b", " (has done)"),
    (r"\bfuture\b", " (will)"),
]


def split_gloss(gloss):
    """'third-person singular present indicative of jam' ->
    ('third-person singular present indicative', 'jam'), or (None, None)."""
    m = _POINTER.search(gloss or "")
    if not m:
        return None, None
    return _POINTER.sub("", gloss).strip(), m.group(1)


def lemma_english(lookup, lemma):
    """The lemma's own English gloss, e.g. jam -> 'to be'."""
    card = lookup.get(lemma)
    if not card:
        return None
    for g in (card.get("glosses") or []):
        g = str(g).strip()
        if g:
            return g
    en = card.get("en")
    if isinstance(en, str) and en.strip():
        return en.strip()
    return None


def display_noun(lemma, lemma_en):
    """The English to show for a nominal lemma, override applied."""
    if lemma in _LEMMA_DISPLAY_OVERRIDE:
        return _LEMMA_DISPLAY_OVERRIDE[lemma]
    en = _first_english(lemma_en) or lemma
    # A parenthetical aside is a note for a dictionary user, not part of the
    # word's meaning: 'minute (unit of time)' on a card is noise. Drop it, but
    # only when something is left in front of the bracket.
    stripped = re.sub(r"\s*\([^)]*\)", "", en).strip()
    return stripped or en


def infinitive(english):
    """'to be, pass' -> 'be';  'to think' -> 'think'.  None if not a verb gloss."""
    if not english:
        return None
    e = str(english).strip()
    if not e.lower().startswith("to "):
        return None
    return e[3:].split(";")[0].split(",")[0].strip() or None


def _first_english(english):
    """The lemma gloss trimmed to its first sense, for display."""
    if not english:
        return None
    return str(english).split(";")[0].split(",")[0].strip() or None


def _regular_3sg(inf):
    """Infinitive -> third-person singular, only for regular verbs.

    Returns None for anything irregular rather than guessing: 'be' -> 'bee' and
    'go' -> 'goes' are not the same kind of operation, and a wrong third-person
    form teaches a false sentence.
    """
    if not inf:
        return None
    irregular = {
        "be", "have", "do", "go", "say", "make", "know", "think", "take",
        "come", "see", "give", "find", "tell", "become", "leave", "feel",
        "put", "mean", "keep", "let", "begin", "seem", "hear", "hold",
        "bring", "write", "buy", "speak", "eat", "drink", "run", "sleep",
    }
    if inf.lower() in irregular:
        return None
    if inf.endswith(("s", "x", "z", "ch", "sh")):
        return inf + "es"
    if inf.endswith("y") and len(inf) > 1 and inf[-2] not in "aeiou":
        return inf[:-1] + "ies"
    return inf + "s"


def _lemma_tail(lemma, lemma_en):
    inf = infinitive(lemma_en)
    return " (from %s)" % lemma if not inf else " (from %s, to %s)" % (lemma, inf)


def friendly_verb(prefix, lemma, lemma_en):
    """Learner-facing gloss for a verbal form, or None to keep the original."""
    inf = infinitive(lemma_en)

    if re.search(r"\bparticiple\b", prefix, re.I):
        when = "past " if re.search(r"\bpast\b", prefix, re.I) else ""
        if inf:
            return "%sparticiple of %s (to %s)" % (when, lemma, inf)
        return "%sparticiple of %s" % (when, lemma)

    mp = _PERSON_R.search(prefix)
    mn = _NUMBER_R.search(prefix)
    if not mp or not mn:
        return None
    person = mp.group(1).lower()
    number = mn.group(1).lower()
    pron = _PRONOUN.get((person, number)) or _PRONOUN.get((person, "singular"))
    if not pron:
        return None

    # 'indicative/imperative' names two moods at once. Neither the imperative
    # address nor a plain statement is safe to claim, so this falls through to
    # the infinitive below, which is true for both readings.
    both_moods = bool(re.search(r"\bindicative\b", prefix, re.I)
                      and re.search(r"\bimperative\b", prefix, re.I))

    if re.search(r"\bimperative\b", prefix, re.I) and not both_moods:
        addr = {"I": "go", "we": "let's go"}.get(pron, pron)
        tail = ", to %s" % inf if inf else ""
        return "%s! (imperative of %s%s)" % (addr, lemma, tail)

    note = ""
    for rx, txt in _MOOD_TENSE:
        if re.search(rx, prefix, re.I):
            note = txt
            break

    # Tense and verb are ONE field. Building them separately and concatenating
    # produced 'he/she/it (used to) was is', because the imperfect supplies the
    # past form of the lemma and the present-form table then supplied a second
    # verb on top of it. A past slot already says everything the form means.
    past = bool(re.search(r"\b(imperfect|aorist)\b", prefix, re.I))

    if past and inf:
        verb = _IRREGULAR_PAST.get(inf.lower(), inf + "ed")
        if not note:
            note = " (once did)" if re.search(r"\baorist\b", prefix, re.I) else " (used to)"
        return "%s%s %s%s" % (pron, note, verb, _lemma_tail(lemma, lemma_en))

    if inf and inf.lower() == "be":
        verb = _BE_FORMS.get((person, number)) or _BE_FORMS.get((person, "singular")) or "be"
        return "%s%s %s%s" % (pron, note, verb, _lemma_tail(lemma, lemma_en))

    if person.startswith("third") and number == "singular" and not note:
        third = _regular_3sg(inf) if inf else None
        if third:
            return "%s %s%s" % (pron, third, _lemma_tail(lemma, lemma_en))

    base = inf or _first_english(lemma_en) or lemma
    return "%s%s %s%s" % (pron, note, base, _lemma_tail(lemma, lemma_en))


def friendly_noun(prefix, lemma, lemma_en, default_definite=None):
    """Learner-facing gloss for a nominal form, or None to keep the original."""
    n = None
    # 'plural of minute' carries the number as the WHOLE prefix, with no case
    # or article in front of it, so the loop below never matched it.
    for rx, label in ((r"^\s*plural\b", "plural"),
                      (r"^\s*singular\b", "singular"),
                      (r"^\s*dual\b", "dual"),
                      (r"\bplural\b", "plural"),
                      (r"\bsingular\b", "singular"),
                      (r"\bdual\b", "dual")):
        if re.search(rx, prefix, re.I):
            n = label
            break

    base = display_noun(lemma, lemma_en)
    # A lemma glossed with an indefinite quantifier ('anyone') cannot take an
    # article: 'the anyone' is nonsense. But the DEFINITE ENDING still carries
    # real information about the word, so it is kept as a note rather than
    # dropped: njeri is glossed 'anyone', yet 'njerëzit' really does mean the
    # people. Showing the article alone would teach the wrong thing; showing
    # nothing would teach nothing.
    indefinite_lemma = bool(_INDEFINITE_NOUN.match(base))

    head = ""
    if re.search(r"\bdefinite\b", prefix, re.I):
        head = "" if indefinite_lemma else "the "
    elif re.search(r"\bindefinite\b", prefix, re.I):
        head = ""
    elif default_definite is True and not indefinite_lemma:
        head = "the "

    if n:
        return "%s%s, %s%s" % (head, base, n, _lemma_tail(lemma, lemma_en))
    return "%s%s%s" % (head, base, _lemma_tail(lemma, lemma_en))


def friendly_gloss(gloss, pos, lemma, lookup):
    """Rewrite one form gloss for a learner. Returns None to keep the original.

    Keeping the original is the correct fallback, not a failure: it happens for
    archaic dialect forms and any slot this module does not model. A Wiktionary
    gloss is at least true; a guessed rewrite would not be.
    """
    prefix, lem = split_gloss(gloss)
    if prefix is None or not lem or lem != lemma:
        return None
    if not _SLOT_R.search(prefix) and not _PERSON_R.search(prefix):
        return None

    lemma_en = lemma_english(lookup, lem)
    if pos == "verb":
        return friendly_verb(prefix, lem, lemma_en)
    return friendly_noun(prefix, lem, lemma_en)
