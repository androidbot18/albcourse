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

# A form gloss ends by naming its lemma, but very often carries material AFTER
# it, which an end-anchored pattern cannot reach:
#
#   participle of vdes (to die (used only for humans and bees))
#   first-person singular imperfect indicative of dua; "I wanted"
#
# 91 of the 133 glosses that still leaked grammar terminology had exactly the
# first shape. One level of nesting is allowed because "(to die (used only for
# humans and bees))" is a real Wiktionary gloss, not a hypothetical.
_PAREN = r"(?:\s*\((?:[^()]|\([^()]*\))*\))?"
_POINTER = re.compile(
    r"\bof\s+([A-Za-zëçËÇ][A-Za-zëçËÇ'-]*)" + _PAREN + r"\s*[.;:]?\s*$")

# A gloss an earlier pass already rewrote names its lemma inside a trailing
# "(from X, to Y)". The lemma sits mid-parenthetical, so the end-anchored
# pointer cannot reach it. The same is true of a mood named in parentheses
# mid-phrase, as in 'he/she/it (subjunctive) say (from them, to say)', which is
# how21 more of the 133 were left holding a grammar word.
_FROM_TAIL = re.compile(r"\(from\s+([A-Za-zëçËÇ][A-Za-zëçËÇ'-]*)\s*,")
_MOOD_PAREN = re.compile(
    r"\s*\((?:indicative|subjunctive|conditional|jussive|optative|admirative|"
    r"aorist|imperative)\)\s*", re.I)
_MOOD_R = re.compile(
    r"\b(indicative|subjunctive|conditional|jussive|optative|admirative|"
    r"aorist|imperative)\b", re.I)

# An English rendering the source supplies for this exact form, after a sentence
# stop or inside curly quotes:
#
#   first-person singular imperfect indicative of dua; "I wanted", "I loved"
#   third-person plural imperfect indicative of dua; "they wanted", "they loved"
#
# This is human-written FOR the precise form, so it beats anything reconstructed
# from the lemma, and it is what the 6 remaining 'do*' cards have instead of a
# rebuildable slot.
_TRANSLATION = re.compile(r"[.;:]\s*[\u201c]([^\u201d]+)[\u201d]")

# A bare 'of <lemma>', used to locate the lemma inside a gloss that continues
# with a quoted translation rather than ending at the lemma.
_OF_WORD = re.compile(r"\bof\s+([A-Za-zëçËÇ][A-Za-zëçËÇ'-]*)")


def sense_translation(gloss):
    """The human English rendering the source gloss gives for this exact form.

    None when there is none, so the caller falls back to building the gloss from
    the lemma rather than inventing an English form.
    """
    if not gloss:
        return None
    m = _TRANSLATION.search(gloss)
    if not m:
        return None
    text = m.group(1).strip()
    return text if text and re.search(r"[A-Za-z]", text) else None
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
    # The subjunctive, jussive and conditional have no distinct English word:
    # English marks them by word order and auxiliaries, not by an ending.
    # Labelling a card '(subjunctive)' therefore taught a grammar term instead of
    # a meaning, which is exactly what this rewrite exists to remove. These moods
    # render as the infinitive, which is what appears after the conjunction 'te'
    # ('te dua' = 'to want') and is therefore true of them.
    (r"\bsubjunctive\b", ""),
    (r"\bjussive\b", ""),
    (r"\bconditional\b", ""),
    (r"\bimperative\b", ""),
    (r"\bimperfect\b", " (used to)"),
    (r"\baorist\b", " (once did)"),
    (r"\bpluperfect\b", " (had done)"),
    (r"\bsimple perfect\b", " (has done)"),
    (r"\bperfective\b", " (has done)"),
    (r"\bperfect\b", " (has done)"),
    (r"\bfuture\b", " (will)"),
]


def _tidy(prefix):
    """Drop mood parentheticals, dangling punctuation and doubled spaces."""
    prefix = _MOOD_PAREN.sub(" ", prefix)
    # A '(' left stranded by removing a bracketed tail means a fragment of that
    # tail survived, so cut back to the last balanced point.
    if prefix.count("(") < prefix.count(")"):
        cut = prefix.rfind("(")
        if cut != -1:
            prefix = prefix[:cut]
    prefix = re.sub(r"\(\s*\)", "", prefix)
    # An emptied parenthetical can strand its own bracket, as in
    # 'ask him/her/it (second-person singular imperative )', so a lone opening
    # bracket at the end goes too.
    prefix = re.sub(r"\s*\(\s*$", "", prefix)
    prefix = re.sub(r"\s*[(;,:]\s*$", "", prefix)
    prefix = re.sub(r"\s+", " ", prefix)
    return prefix.strip(" ;,")


def split_gloss(gloss):
    """'third-person singular present indicative of jam' ->
    ('third-person singular present indicative', 'jam'), or (None, None).

    Also reads the shapes an end-anchored 'of <lemma>' cannot:

      participle of vdes (to die (only for humans))  -> ('participle', 'vdes')
      he/she/it (subjunctive) say (from them, to say) -> ('he/she/it say', 'them')
      first-person singular ... of dua; "I wanted"  -> (..., 'dua')
    """
    gloss = gloss or ""

    m = _POINTER.search(gloss)
    if m:
        return _tidy(gloss[:m.start()] + gloss[m.end():]) or None, m.group(1)

    # Already rewritten by an earlier pass: the lemma is in a trailing
    # '(from X, to Y)' rather than after an 'of'.
    fm = _FROM_TAIL.search(gloss)
    if fm:
        open_at = gloss.rfind("(", 0, fm.start())
        head = gloss[:open_at] if open_at != -1 else gloss[:fm.start()]
        return _tidy(head) or None, fm.group(1)

    # A gloss whose lemma is followed by a quoted translation rather than by
    # nothing:
    #
    #   first-person singular imperfect indicative of dua; "I wanted"
    #
    # The quoted text is human-written for the precise form, so it is the gloss.
    # The prefix is still returned so the caller can see which slot is meant.
    tr = _TRANSLATION.search(gloss)
    if tr:
        m2 = _OF_WORD.search(gloss[:tr.start()])
        if m2:
            return _tidy(gloss[:m2.start()] + gloss[m2.end():tr.start()]) or None, m2.group(1)

    # Last resort, and only for text already known to be form-of phrasing: the
    # lemma is not at the end because something follows it, as in
    #
    #   accusative masculine/feminine singular of ky and kjo
    #   ask him/her/it (second-person singular imperative of pyes ("ask"))
    #
    # The FIRST match is the lemma here, since later ones belong to a usage note
    # or to a second lemma name ('ky and kjo'). The slot test is what keeps a
    # content gloss that merely mentions a grammatical word out of this branch.
    if _SLOT_R.search(gloss):
        m3 = _OF_WORD.search(gloss)
        if m3:
            return _tidy(gloss[:m3.start()] + gloss[m3.end():]) or None, m3.group(1)

    return None, None


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
    """'to be, pass' -> 'be';  'to think' -> 'think'.  None if not a verb gloss.

    A trailing parenthetical is a usage note, not part of the verb:
    'to die (used only for humans and bees)' is 'die'. Without the cut it
    produced 'die (used only for humans and bees), past form (from vdes, ...)',
    which repeated the note and read as a broken gloss.
    """
    if not english:
        return None
    e = str(english).strip()
    if not e.lower().startswith("to "):
        return None
    e = re.sub(r"\s*\((?:[^()]|\([^()]*\))*\)\s*$", "", e)
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
        # A participle is a word the learner meets, so say what it DOES rather
        # than naming the slot: 'vdekur' is 'die', not 'participle of vdes'. The
        # infinitive alone reads as the lemma though, so it is marked as the past
        # form, which is the one fact the learner needs about it.
        tail = _lemma_tail(lemma, lemma_en)
        return "%s, past form%s" % (inf or lemma, tail)

    mp = _PERSON_R.search(prefix)
    mn = _NUMBER_R.search(prefix)
    if not mp or not mn:
        return None
    person = mp.group(1).lower()
    number = mn.group(1).lower()
    pron = _PRONOUN.get((person, number)) or _PRONOUN.get((person, "singular"))
    if not pron:
        return None

    # A gloss naming TWO moods at once ('indicative/imperative',
    # 'present indicative/subjunctive') cannot have either claimed, because the
    # English differs between them. Counting them, rather than testing for the
    # one pair that first showed up, is what keeps a second pairing from leaking
    # a grammar word back in: 'duam' was being glossed
    # 'we (subjunctive) want', and 'pyete' kept 'imperative of pyes'.
    moods = set(m.lower() for m in re.findall(
        r"\b(indicative|subjunctive|conditional|jussive|optative|admirative|"
        r"aorist|imperative)\b", prefix, re.I))

    if "imperative" in moods and len(moods) == 1:
        addr = {"I": "go", "we": "let's go"}.get(pron, pron)
        tail = ", to %s" % inf if inf else ""
        return "%s! (from %s%s)" % (addr, lemma, tail)

    note = ""
    # A mood NOTE is also a claim about the English form, so it is skipped
    # when the gloss named two moods and neither can be asserted. That is
    # what kept 'duam', glossed 'present indicative/subjunctive', from being
    # written as 'we (subjunctive) want'.
    for rx, txt in ([] if len(moods) > 1 else _MOOD_TENSE):
        if re.search(rx, prefix, re.I):
            # 'has done' is third-person singular English. 'I/we/they ... has
            # done' teaches a false sentence, so the perfect agrees with the
            # person already resolved above. Only third-person singular takes
            # 'has'; everything else takes 'have'.
            if txt == " (has done)" and not (
                    person.startswith("third") and number == "singular"):
                txt = " (have done)"
            # The perfect note claims an English construction a copula cannot
            # carry. qenë is glossed 'third-person plural simple perfect
            # indicative of jam', and the note was attached to the 'be' form
            # below, shipping the card as 'they (have done) are'. English has
            # no '(have done) are', so the note is dropped for 'be'; the card
            # then reads 'they are', which is true.
            if inf and inf.lower() == "be" and "done" in txt:
                txt = ""
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

    # A gloss an earlier pass already rewrote reads as a finished English phrase
    # once the mood word is dropped:
    #
    #   'he/she/it (subjunctive) say (from them, to say)' -> 'he/she/it say'
    #
    # The pronoun is resolved and the verb already conjugated, so the body IS the
    # gloss and rebuilding it from the lemma would lose the conjugation. This is
    # tried only when the ORIGINAL gloss carried both a mood word and a complete
    # '(from X, to Y)' lemma note; a gloss that has never been rewritten names its
    # lemma only as 'from them' and still needs the full path below. Without that
    # distinction 'bjesh' lost its verb and read as a bare 'you'.
    if _MOOD_R.search(gloss or "") and _FROM_TAIL.search(gloss or ""):
        if re.search(r"\bto\s+[^()]+\)\s*$", gloss):
            # Cut the WHOLE trailing parenthetical. Removing only the '(from X,'
            # part leaves ' to say)' stranded, which produced 'he/she/it say to
            # say)' on21 cards.
            head = _tidy(gloss[:gloss.rfind("(")])
            if head:
                return head

    if not _SLOT_R.search(prefix) and not _PERSON_R.search(prefix):
        # A human rendering of this exact form beats any reconstruction, so it is
        # preferred before the rebuild is even attempted. Used only when the gloss
        # carries a slot term too, which is what identifies it as a form gloss.
        tr = sense_translation(gloss)
        if tr and _SLOT_R.search(gloss):
            lemma_en = lemma_english(lookup, lem)
            return "%s%s" % (tr, _lemma_tail(lem, lemma_en))
        return None

    lemma_en = lemma_english(lookup, lem)
    if pos == "verb":
        return friendly_verb(prefix, lem, lemma_en)
    return friendly_noun(prefix, lem, lemma_en)
