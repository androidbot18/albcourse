"""Core words Wiktionary lacks, added by hand (RECOMMENDATIONS.md section 3.6).

The deck is built from Wiktionary, so a word with no Albanian entry there can
never become a card, however common it is. Measured against the pinned
frequency list, 292 of the 1,411 forms that make up 80% of tokens had no
entry at all. Most of those are names, interjections (`oh`, `hej`) or
ë-less misspellings (`mire`, `kete`), which do not belong in a course. The
rest are everyday words: `pra` (rank 93), `ndonjë` (114), `sikur`,
`vërtet`, `sigurisht`, `problem`, `fakt`, `mirupafshim`...

This is the overrides layer for them, like tools/gloss_overrides.py. Each
entry is a whole card: part of speech, headline gloss (plus any further
senses), one reviewed example, and the inflected forms a learner meets. The
build adds a card only when Wiktionary gave it none (tools/build_course.py
fails otherwise, so an entry cannot shadow real data), and only for a word
the frequency list has, which supplies its rank.

What is deliberately NOT here:

  * inflected forms of words the deck already teaches (`gjitha` is
    `të gjitha`, a form of `gjithë`; `djema`, `veten`, `vdiq`). They count
    towards coverage through their lemma; see tools/measure_coverage.py.
  * clitic clusters (`ma`, `ia`, `ua`, `iu`): grammar, not vocabulary.
  * misspellings, names, English (`ok`), interjections (`oh`, `uh`), and
    insults.

Keys per entry:

  pos      one of build_course.CORE_POS
  senses   glosses, headline first
  ex       (Albanian, English), a short sentence using the word itself
  forms    [(form, tag), ...], tags as in Wiktionary's own form lists
  form_of  the lemma this word is an inflection of; the card then joins
           that lemma's family, exactly like a Wiktionary form card

A native speaker should review every gloss and example here; PLAN.md lists
this file in the review pass.
"""
import re

WORDS = {
    # ---- discourse words: the glue of every spoken sentence
    "pra": {"pos": "conj", "senses": ["so, then, therefore"],
            "ex": ("Pra, nesër shkojmë.", "So we're going tomorrow.")},
    "ndonjë": {"pos": "det", "senses": ["any, some (one or other)"],
               "ex": ("A ke ndonjë pyetje?", "Do you have any questions?")},
    "sikur": {"pos": "conj", "senses": ["as if, as though", "if only"],
              "ex": ("Flet sikur di gjithçka.",
                     "He talks as if he knows everything.")},
    "vërtet": {"pos": "adv", "senses": ["really, truly; indeed"],
               "ex": ("Është vërtet e bukur.", "It's really beautiful.")},
    "sigurisht": {"pos": "adv", "senses": ["of course, certainly"],
                  "ex": ("Sigurisht që vij.", "Of course I'm coming.")},
    "natyrisht": {"pos": "adv", "senses": ["naturally, of course"],
                  "ex": ("Natyrisht që e di.", "Of course I know.")},
    "seriozisht": {"pos": "adv", "senses": ["seriously"],
                   "ex": ("Flas seriozisht.", "I'm serious.")},
    "epo": {"pos": "intj", "senses": ["well, well then"],
            "ex": ("Epo, çfarë të bëjmë?", "Well, what shall we do?")},
    "sapo": {"pos": "adv", "senses": ["just (has just done)",
                                      "as soon as"],
             "ex": ("Sapo erdha.", "I've just arrived.")},
    "derisa": {"pos": "conj", "senses": ["until", "while, since"],
               "ex": ("Prit derisa të vij.", "Wait until I come.")},
    "sesa": {"pos": "conj", "senses": ["than"],
             "ex": ("Sot është më mirë sesa dje.",
                    "Today is better than yesterday.")},
    "gjithsesi": {"pos": "adv", "senses": ["anyway, in any case"],
                  "ex": ("Faleminderit gjithsesi.", "Thanks anyway.")},
    "tamam": {"pos": "adv", "senses": ["exactly, just right"],
              "ex": ("Tamam kështu.", "Exactly like this.")},
    "pothuajse": {"pos": "adv", "senses": ["almost, nearly"],
                  "ex": ("Pothuajse mbarova.", "I'm almost done.")},
    # Wiktionary files madje as a particle, a POS the build skips.
    "madje": {"pos": "adv", "senses": ["even; in fact, what's more"],
              "ex": ("Ai nuk humbi asgjë, madje fitoi!",
                     "He didn't lose anything; he even won!")},
    "ndryshe": {"pos": "adv", "senses": ["differently; otherwise"],
                "ex": ("Tani është ndryshe.", "Now it's different.")},

    # ---- place and time
    "lart": {"pos": "adv", "senses": ["up, upstairs; above"],
             "ex": ("Ai është lart.", "He's upstairs.")},
    "përpara": {"pos": "adv", "senses": ["forward, ahead",
                                         "in front of, before"],
                "ex": ("Shko përpara!", "Go ahead!")},
    "kudo": {"pos": "adv", "senses": ["everywhere; anywhere"],
             "ex": ("Të kërkova kudo.", "I looked for you everywhere.")},
    "përmes": {"pos": "prep", "senses": ["through, across"],
               "ex": ("Kaluam përmes pyllit.",
                      "We went through the forest.")},
    "njëherë": {"pos": "adv", "senses": ["once", "for a moment, first"],
                "ex": ("E pashë vetëm njëherë.", "I saw it only once.")},
    "asnjëherë": {"pos": "adv", "senses": ["never"],
                  "ex": ("Nuk e kam parë asnjëherë.",
                         "I have never seen it.")},
    # Fixed phrases: the frequency list counts the second word, and the
    # card says the whole phrase.
    "bashku": {"pos": "adv", "senses": ["together (së bashku)"],
               "ex": ("Shkojmë së bashku.", "Let's go together.")},
    "paktën": {"pos": "adv", "senses": ["at least (të paktën)"],
               "ex": ("Të paktën provo.", "At least try.")},
    "shpejti": {"pos": "adv", "senses": ["soon (së shpejti)"],
                "ex": ("Shihemi së shpejti.", "See you soon.")},

    # ---- greetings
    # Wiktionary has mirupafshim only as an "alternative form of mirë u
    # pafshim", which is not a gloss, so the card never formed.
    "mirupafshim": {"pos": "intj", "senses": ["goodbye"],
                    "ex": ("Faleminderit, mirupafshim!",
                           "Thank you, goodbye!")},
    # Wiktionary's only entry is the phrase "më falni".
    "falni": {"pos": "verb", "form_of": "fal",
              "senses": ["excuse me, sorry (më falni; from fal, to forgive)"],
              "ex": ("Më falni, ku është stacioni?",
                     "Excuse me, where is the station?")},

    # ---- nouns and adjectives
    "problem": {"pos": "noun", "senses": ["problem"],
                "ex": ("Nuk ka problem.", "No problem."),
                "forms": [("probleme", "plural"), ("problemi", "definite"),
                          ("problemin", "accusative"),
                          ("problemet", "plural")]},
    "fakt": {"pos": "noun", "senses": ["fact (në fakt, in fact)"],
             "ex": ("Në fakt, nuk e di.", "In fact, I don't know."),
             "forms": [("fakte", "plural"), ("fakti", "definite"),
                       ("faktin", "accusative")]},
    "moment": {"pos": "noun", "senses": ["moment"],
               "ex": ("Një moment, të lutem.", "One moment, please."),
               "forms": [("momente", "plural"), ("momenti", "definite"),
                         ("momentin", "accusative")]},
    "plan": {"pos": "noun", "senses": ["plan"],
             "ex": ("Kam një plan.", "I have a plan."),
             "forms": [("plane", "plural"), ("plani", "definite"),
                       ("planin", "accusative")]},
    "person": {"pos": "noun", "senses": ["person"],
               "ex": ("Është një person i mirë.", "He's a good person."),
               "forms": [("persona", "plural"), ("personi", "definite"),
                         ("personin", "accusative")]},
    "ide": {"pos": "noun", "senses": ["idea"],
            "ex": ("Kam një ide.", "I have an idea."),
            "forms": [("ideja", "definite"), ("idenë", "accusative"),
                      ("idetë", "plural")]},
    "shef": {"pos": "noun", "senses": ["boss, chief"],
             "ex": ("Ai është shefi im.", "He's my boss."),
             "forms": [("shefa", "plural"), ("shefi", "definite"),
                       ("shefin", "accusative")]},
    "polic": {"pos": "noun", "senses": ["police officer"],
              "ex": ("Ai është polic.", "He's a police officer."),
              "forms": [("policë", "plural"), ("polici", "definite"),
                        ("policin", "accusative")]},
    "milion": {"pos": "noun", "senses": ["million"],
               "ex": ("Një milion njerëz.", "A million people."),
               "forms": [("milionë", "plural"), ("milioni", "definite")]},
    "dollar": {"pos": "noun", "senses": ["dollar"],
               "ex": ("Kushton dhjetë dollarë.", "It costs ten dollars."),
               "forms": [("dollarë", "plural"), ("dollari", "definite"),
                         ("dollarët", "plural")]},
    "siguri": {"pos": "noun", "senses": ["safety, security",
                                         "certainty (me siguri, for sure)"],
               "ex": ("E di me siguri.", "I know it for sure."),
               "forms": [("siguria", "definite"),
                         ("sigurinë", "accusative")]},
    # Adjectives take the linking article, so the card shows it, and the
    # forms carry the feminine and plural a learner reads far more often
    # than the bare masculine.
    "sigurt": {"pos": "adj", "senses": ["sure, certain; safe (i sigurt)"],
               "ex": ("Je i sigurt?", "Are you sure?"),
               "forms": [("sigurtë", "feminine"), ("sigurta", "plural")]},
    "tmerrshëm": {"pos": "adj", "senses": ["terrible, awful (i tmerrshëm)"],
                  "ex": ("Ishte një ditë e tmerrshme.",
                         "It was a terrible day."),
                  "forms": [("tmerrshme", "feminine")]},
    "fantastik": {"pos": "adj", "senses": ["fantastic, great"],
                  "ex": ("Është një ide fantastike.",
                         "It's a fantastic idea."),
                  "forms": [("fantastike", "feminine"),
                            ("fantastikë", "plural")]},
}


def apply(cards, freq, pos_label, word_re):
    """Append a card for every entry. Returns the words added.

    Raises if an entry names a word Wiktionary already gave a card (the hand
    entry would shadow real data), a word the frequency list lacks, or a
    malformed entry: this list is small and reviewed, so a bad entry is a
    mistake to fix, not to skip.
    """
    have = {c["word"] for c in cards}
    added = []
    for w in sorted(WORDS):
        e = WORDS[w]
        if w in have:
            raise ValueError("added_words: %r already has a Wiktionary card"
                             % w)
        if w not in freq:
            raise ValueError("added_words: %r is not in the frequency list"
                             % w)
        if not word_re.match(w) or not e.get("senses"):
            raise ValueError("added_words: malformed entry %r" % w)
        sq, en = e["ex"]
        # The example must use the word or one of its listed forms, as a
        # whole token: "e tmerrshme" teaches tmerrshëm.
        hit = None
        for form in [w] + [f for f, _ in e.get("forms", [])]:
            hit = re.search(r"(?<!\w)%s(?!\w)" % re.escape(form), sq, re.I)
            if hit:
                break
        if not hit:
            raise ValueError("added_words: %r's example does not use it" % w)
        rank, count = freq[w]
        senses = []
        for i, gloss in enumerate(e["senses"]):
            s = {"pos": e["pos"], "pos_label": pos_label(e["pos"]),
                 "gloss": gloss, "tags": [], "cats": [], "examples": [],
                 "links": [], "_score": 0, "_src": i}
            if e.get("form_of"):
                s["is_form_of"] = e["form_of"]
            senses.append(s)
        senses[0]["examples"] = [{"sq": sq, "en": en,
                                  "offsets": [[hit.start(), hit.end()]]}]
        cards.append({
            "word": w, "rank": rank, "count": count, "senses": senses,
            "etymology": "", "etymology_class": None, "parents": [],
            "source_lang": None, "derived": [], "related": [],
            "forms": [{"form": f, "tag": t} for f, t in e.get("forms", [])],
        })
        added.append(w)
    cards.sort(key=lambda c: (c["rank"], c["word"]))
    return added


def lemma_forms():
    """{form: lemma} for every listed form, for coverage counting."""
    return {f: w for w, e in WORDS.items() for f, _ in e.get("forms", [])}
