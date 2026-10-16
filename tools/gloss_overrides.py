"""Reviewed fixes to headline glosses (RECOMMENDATIONS.md section 4.1).

The build picks a word's headline from Wiktionary's sense order, which is
sometimes wrong for a learner: `në` opened with "if" (its rarer conjunction
sense) and `botë` with "Earth". This is the small, hand-reviewed overrides
layer section 3.2 argues for. Each entry is applied after the build has
chosen its senses, so it survives a rebuild.

  RENAME   reword an existing sense (matched by exact gloss); None drops it
  ADD      insert a sense Wiktionary lacks, at a given position
  FRONT    move existing senses (matched by exact gloss) to the front, in order
  REPLACE  replace the headline sense's gloss (and POS) outright
  EXAMPLES a reviewed example sentence for a sense, shown before any other

The words of the curated opening (tools/opening_levels.py) were all checked
here: a learner's first cards must not headline `pi` as "from" or `kafe` as
"a plant of the genus Coffea".
"""
import re

RENAME = {
    "e": {
        # Two of its three readings, reworded so the card says what each
        # one does. "and" stays the headline.
        "of (+ dative)":
            "the linking article: of (shtëpia e mikut, the friend's house)",
        "third-person singular accusative-case pronominal clitic (him, her, "
        "it) corresponding to pronouns ai and ajo (see there for declension "
        "tables)": "it, him, her (before a verb: e di, I know it)",
        # A grammar label, not a meaning.
        "masculine singular preposition, plural preposition": None,
    },
    "kafe": {"ground coffee beans, the beverage brewed from it": "coffee",
             "Brown": "brown"},
    "pi": {"to drink, to suck": "to drink"},
    "lutem": {
        "(used to underline politeness when acknowledging (or refusing) an "
        "offer, gift, service or compliment) + pronoun: please, welcome":
            "please (ju lutem); you're welcome",
    },
    "nuk": {"Negates the meaning of the modified verb: not, don't":
            "not, don't (before a verb: nuk di, I don't know)"},
    "jo": {"negates non-verbal phrases: no, not": "no; not"},
    # Days of the week. Each is said with its article, and "on Monday" is
    # the definite accusative after të; the card has to show both, because
    # the bare word on its own is not how a learner meets it.
    "hënë": {"Monday": "Monday (e hënë; të hënën, on Monday)"},
    "martë": {"Tuesday": "Tuesday (e martë; të martën, on Tuesday)"},
    "mërkurë": {"Wednesday":
                "Wednesday (e mërkurë; të mërkurën, on Wednesday)"},
    "enjte": {"Thursday": "Thursday (e enjte; të enjten, on Thursday)"},
    "premte": {"Friday": "Friday (e premte; të premten, on Friday)"},
    "shtunë": {"Saturday": "Saturday (e shtunë; të shtunën, on Saturday)"},
    "diel": {"Sunday": "Sunday (e diel; të dielën, on Sunday)"},
}

# (position, pos, gloss)
ADD = {
    # ka has its own entry (the preposition "from"), so it never got the
    # form card it needs as the 3sg of kam.
    "ka": (0, "verb", "he/she/it has (from kam, to have)"),
    # The sense çfarë ("what", ç' + farë) is built on.
    "farë": (1, "noun", "kind, sort (një farë, a sort of)"),
}

FRONT = {
    "në": ["in", "at"],          # the "if" sense is secondary
    "botë": ["world, planet"],   # not "Earth"
    "kafe": ["coffee"],
    "pi": ["to drink"],          # not the Gheg preposition "from"
    "qumësht": ["milk"],         # not the adverb "very (white), as milk"
    "lutem": ["please (ju lutem); you're welcome"],
    # Taught with the days; "moon" stays as the second sense.
    "hënë": ["Monday (e hënë; të hënën, on Monday)"],
}

REPLACE = {
    # do is the future marker ("do të shkoj", I will go) and the 3sg of dua.
    "do": ("verb", "will (future: do të + verb); wants (from dua, to want)"),
    "qenë": ("verb", "been (participle of jam, to be)"),
    "ishin": ("verb", "they were (from jam, to be)"),
    # Its only real senses were "eclipse", "darken" and "obscure".
    "errësirë": ("noun", "darkness"),
}

# {word: (gloss of the sense, Albanian, English)}. Reviewed by hand: `e`'s
# corpus example showed the article under the gloss "and", so its card uses
# this instead and its corpus example is dropped (see corpus_overridden()).
# "ditë e natë" (day and night) is a set phrase, and `e` joins two nouns
# there, so it cannot be read as the article. `pi`'s corpus sentence was
# "A pi drogë?" ("Do you take drugs?"), on a card in the first lessons.
#
# An opening card's reviewed example uses only words taught by its level
# (tools/test_opening_levels.py checks this), so a learner can read it.
EXAMPLES = {
    "e": ("and", "Punoj ditë e natë.", "I work day and night."),
    "pi": ("to drink", "Unë pi kafe me qumësht.",
           "I drink coffee with milk."),
    # Four days had no example at all. Each shows the day with its article.
    "mërkurë": ("Wednesday (e mërkurë; të mërkurën, on Wednesday)",
                "Sot është e mërkurë.", "Today is Wednesday."),
    "premte": ("Friday (e premte; të premten, on Friday)",
               "Nesër është e premte.", "Tomorrow is Friday."),
    "shtunë": ("Saturday (e shtunë; të shtunën, on Saturday)",
               "Sot është e shtunë.", "Today is Saturday."),
    "diel": ("Sunday (e diel; të dielën, on Sunday)",
             "Nesër është e diel.", "Tomorrow is Sunday."),
}

# Corpus sentences that are wrong for the card, with no replacement yet.
DROP_CORPUS = {
    # "Farë është Darodari?" -- a line from a referral-spam site, and farë
    # is a curated opening card.
    "farë",
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
        if w in RENAME:
            ren = RENAME[w]
            senses[:] = [dict(x, gloss=ren[x["gloss"]]) if x["gloss"] in ren
                         else x for x in senses
                         if not (x["gloss"] in ren and ren[x["gloss"]] is None)]
        if w in ADD and senses:
            at, pos, gloss = ADD[w]
            new = dict(senses[0], pos=pos, pos_label=pos_label(pos),
                       gloss=gloss, tags=[], examples=[], links=[])
            if "cats" in new:
                new["cats"] = []
            senses.insert(at, new)
        if w in FRONT:
            front = [s for g in FRONT[w] for s in senses if s["gloss"] == g]
            senses[:] = front + [s for s in senses if s not in front]
        if w in REPLACE and senses:
            pos, gloss = REPLACE[w]
            senses[0] = dict(senses[0], pos=pos, pos_label=pos_label(pos),
                             gloss=gloss)
        if w in EXAMPLES:
            gloss, sq, en = EXAMPLES[w]
            m = re.search(r"(?<!\w)%s(?!\w)" % re.escape(w), sq, re.I)
            ex = {"sq": sq, "en": en,
                  "offsets": [[m.start(), m.end()]] if m else []}
            for x in senses:
                if x["gloss"] == gloss:
                    x["examples"] = [ex] + list(x.get("examples") or [])
        if senses and senses[0]["gloss"] != before:
            changed += 1
    return changed


def corpus_overridden(word):
    """True when this word's corpus sentence is replaced or dropped."""
    return word in EXAMPLES or word in DROP_CORPUS
