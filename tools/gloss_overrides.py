"""Reviewed fixes to headline glosses (RECOMMENDATIONS.md section 4.1).

The build picks a word's headline from Wiktionary's sense order, which is
sometimes wrong for a learner: `në` opened with "if" (its rarer conjunction
sense) and `botë` with "Earth". This is the small, hand-reviewed overrides
layer section 3.2 argues for. Each entry is applied after the build has
chosen its senses, so it survives a rebuild.

  FRONT    move existing senses (matched by exact gloss) to the front, in order
  REPLACE  replace the headline sense's gloss (and POS) outright
"""
import re

FRONT = {
    "në": ["in", "at"],          # the "if" sense is secondary
    "botë": ["world, planet"],   # not "Earth"
}

REPLACE = {
    # do is the future marker ("do të shkoj", I will go) and the 3sg of dua.
    "do": ("verb", "will (future: do të + verb); wants (from dua, to want)"),
    "qenë": ("verb", "been (participle of jam, to be)"),
    "ishin": ("verb", "they were (from jam, to be)"),
    # Its only real senses were "eclipse", "darken" and "obscure".
    "errësirë": ("noun", "darkness"),
}

# A sense whose "gloss" is Wiktionary's head line ("errësirë f (plural ...")
# rather than a meaning. Such senses carry no translation at all.
HEADLINE_JUNK = re.compile(r"^\S+ [fmn]\b.*\((plural|definite)")


def apply(cards, pos_label):
    """Fix headline glosses in place. Returns the number of cards changed."""
    changed = 0
    for c in cards:
        w, senses = c["word"], c["senses"]
        before = senses[0]["gloss"] if senses else None
        keep = [s for s in senses if not HEADLINE_JUNK.match(s["gloss"])]
        if keep and len(keep) < len(senses):
            senses[:] = keep
        if w in FRONT:
            front = [s for g in FRONT[w] for s in senses if s["gloss"] == g]
            senses[:] = front + [s for s in senses if s not in front]
        if w in REPLACE and senses:
            pos, gloss = REPLACE[w]
            senses[0] = dict(senses[0], pos=pos, pos_label=pos_label(pos),
                             gloss=gloss)
        if senses and senses[0]["gloss"] != before:
            changed += 1
    return changed
