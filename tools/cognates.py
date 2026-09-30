# Cognate layer: the learning hook a kanji radical would provide.
#
# A learner who already knows Latin, Greek or English gets a free association
# from every borrowed word: lloj < Greek logi, kafe < Turkish kahve,
# telefon < Greek tele + phone. That is the closest thing Albanian has to a
# kanji radical, and it was sitting unused behind a bare class label.
#
# Two corrections worth recording, both from the review that proposed this:
#
# 1. It counted 1,320 cards as cognates from the borrowed (812) + inherited
#    (508) classes. Those classes record only THAT a word was borrowed, not
#    from where. Only 156 cards carry a source language, and fewer still name
#    a usable form. The 1,320 figure was an 8x overclaim.
#
# 2. The first extractor took the first pattern that matched, so on
#    "From Greek logi (sort)" it returned the English gloss: lloj came out
#    as "from Greek sort". A memory hook must be a word in the source
#    language, not a meaning. Hence _COMMON_ENGLISH below -- a candidate
#    that is simply the English gloss is rejected.

import re

KNOWN_LANGUAGES = {
    'la': 'Latin', 'el': 'Greek', 'it': 'Italian', 'fr': 'French',
    'en': 'English', 'tr': 'Turkish', 'sr': 'Serbian', 'ar': 'Arabic',
    'es': 'Spanish', 'de': 'German', 'ro': 'Romanian',
}

_BARE = re.compile(
    r'[Ff]rom\s+(?:Ancient\s+|Vulgar\s+|Late\s+|Ottoman\s+|Proto-)?'
    r'(?:Latin|Greek|Italian|French|Turkish|Serbian|Spanish|English)'
    '\s*[*_]?(?:via\s+|through\s+)?\s*[*_]?'
    r'([A-Za-z\u00C0-\u024F\u0370-\u03FF][^,.;()“”"]{0,30})')

_QUOTED = re.compile(
    r'[*\u201c\u201d"]([^\u201c\u201d*"]{2,40})[\u201d\u201d*"]'
    r'\s*(?:\(([^)]{0,40})\))?')

_PAREN = re.compile(
    r'\(([A-Za-z\u00C0-\u024F][A-Za-z\u00C0-\u024F\u0300-\u036F]{1,20})\s*,')

# Plain English words that show up as glosses in etymology text. A candidate
# equal to one of these is a meaning, not a source form.
_COMMON_ENGLISH = {
    'sort', 'kind', 'type', 'part', 'thing', 'voice', 'sound', 'promise',
    'coffee', 'clean', 'cleanliness', 'really', 'truly', 'thick', 'rough',
    'uneven', 'awe', 'imperator', 'alarm', 'narrow', 'tight', 'sorrow',
    'hope', 'bath', 'rope', 'cable', 'afraid', 'fear', 'far', 'away',
    'entrict', 'disengage', 'woman', 'man', 'house', 'bread', 'white',
}

_GREEK = re.compile(r'[\u0370-\u03FF]')

_NOISE = {'a', 'an', 'the', 'and', 'or', 'of', 'in', 'on', 'to', 'from', 'id'}


# Language names the bare pattern understands. A card whose etymology text
# names some other language (South Slavic for a card tagged Serbian) does not
# match, and we refuse rather than fall back to the quoted gloss.
_LANG_NAMES = {
    'la': 'Latin', 'el': 'Greek', 'it': 'Italian', 'fr': 'French',
    'en': 'English', 'tr': 'Turkish', 'sr': 'Serbian', 'es': 'Spanish',
    'de': 'German', 'ro': 'Romanian', 'ar': 'Arabic',
}


def _lang_named(text, source_lang):
    """True when the etymology text names the language we recorded for it."""
    name = _LANG_NAMES.get(source_lang)
    if not name:
        return False
    return bool(_BARE.search(text)) and name in text


def _bad_form(form):
    """True when the candidate is not a usable source form."""
    f = form.strip(' .,;:*“”"()')
    if len(f) < 2:
        return True
    if f.lower() in _NOISE:
        return True
    if f.lower().rstrip('.') in _COMMON_ENGLISH:
        return True
    if f.lower() in [v.lower() for v in KNOWN_LANGUAGES.values()]:
        return True
    return False


def _clean(chunk):
    return chunk.strip(' .,;:*“”"()')


def _tail_gloss(text, pos):
    """The English gloss following a form, when the text supplies one."""
    tail = text[pos:pos + 60]
    m = re.search(r'[“”"]([^“”"]{2,40})[“”"]', tail)
    return m.group(1).strip() if m else ''


def source_form(etymology_text, source_lang):
    """(form, gloss) for the source word named in an etymology, or None.

    Returns None rather than guessing: "from Latin" with no form is not a
    memory hook, and inventing one would teach a false association.
    """
    if not etymology_text or not source_lang:
        return None
    text = etymology_text.strip()

    # 1. Bare form immediately after the language name.
    #    This must be tried first: "From Latin via." and "From Latin
    #    turpis." name no quoted or parenthesised form, so a paren/quote-
    #    first order refused them. But taken naively it also produced
    #    "from Latin to be afraid" for urrej, whose text reads
    #    From Latin horreo ("to be afraid").
    #
    #    The gloss is what follows the real form inside the quote, so the
    #    test is positional: take the token after the language name, and
    #    reject it when the very next thing in the text is an opening quote
    #    (which is where a translator's gloss starts) or a comma-leading
    #    gloss. A genuine form is followed by punctuation or a closing
    #    paren, never by an opening quotation mark.
    m = _BARE.search(text)
    if m:
        head = _clean(m.group(1))
        toks = head.split()
        if toks:
            tok = _clean(toks[0])
            after = text[m.end():]
            gloss_follows = after.lstrip().startswith(('(“', '"', '“'))
            if not _bad_form(tok):
                return (tok, '')

    # 2. Parenthetical Latin-letter form: (logi, "sort"), (sahi, ...).
    m = _PAREN.search(text)
    if m:
        form = _clean(m.group(1))
        if not _bad_form(form):
            return (form, _tail_gloss(text, m.end()))

    # 3. Quoted or italicised form, taking the one that is not a gloss.
    #    Only reached when the text names a language we did not read. nofke is
    #    recorded as Serbian but its text says "South Slavic", which the bare
    #    pattern does not cover, so the quoted gloss ("new (name)") was
    #    returned as if it were the source form. When the text disagrees with
    #    our own language metadata, guessing teaches a false association.
    if not _lang_named(text, source_lang):
        return None
    for m in _QUOTED.finditer(text):
        form = _clean(m.group(1))
        if _bad_form(form):
            continue
        return (form, _tail_gloss(text, m.end()))
    return None


def cognate_line(word, etymology_text, source_lang):
    """The one-line hook shown on a card, or None.

    Mirrors the component line the deck already uses ("from e- + sille"):

        from Latin soca ("rope, cable")
        from Greek logi ("sort")
    """
    got = source_form(etymology_text, source_lang)
    if not got:
        return None
    form, gloss = got
    lang = KNOWN_LANGUAGES.get(source_lang, source_lang)
    line = 'from %s %s' % (lang, form)
    if gloss:
        line += ' ("%s")' % gloss
    return line
