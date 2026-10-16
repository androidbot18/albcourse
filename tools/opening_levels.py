"""The hand-curated opening (RECOMMENDATIONS.md section 3.2).

A frequency list from OpenSubtitles makes a poor syllabus for the first
weeks: greetings came at L56-81, numbers at L189-210, `bukë` (bread) at L393,
and the first levels were whatever the corpus said most often. So the first
levels are set here by hand, by theme, and the scheduler takes over after
them. This is part of the reviewed overrides layer, beside
tools/gloss_overrides.py.

Rules the scheduler enforces on this list (assign_levels() raises if one is
broken, so a bad edit fails the build rather than shipping):

  * every word is a card in the deck, and appears once;
  * a level holds at most 9 words and 6 families, like any other level;
  * a family is curated on ONE level, so it is never scattered;
  * a word's stem is taught on the same level or an earlier one
    (`mirëdita` sits with `ditë`, `çfarë` with `farë`).

A family does not have to be curated whole. `jam` opens with its present
tense here; the rest (ishte, qenë, isha...) comes back later at its own
frequency, on a level that lists the family under `continues`. Its rare
tail, if it has one, still comes back after that as "(rarer words)".

Within a level the cards are shown in teaching order (tools/
teaching_order.py), not in the order listed here.
"""

LEVELS = [
    ("Hello, yes and no",
     ["përshëndetje", "mirëdita", "ditë", "mirë", "po", "jo",
      "faleminderit"]),
    ("I, you, he, she",
     ["unë", "ti", "ty", "ai", "ajo"]),
    ("We, you, they; please",
     ["ne", "ju", "ata", "ato", "lutem"]),
    ("To be",
     ["jam", "je", "është", "jemi", "jeni", "janë"]),
    ("To have",
     ["kam", "ke", "ka", "kemi", "keni", "kanë"]),
    ("Not, and, in, with, for",
     ["nuk", "dhe", "e", "në", "me", "për"]),
    ("One to five",
     ["një", "dy", "tre", "katër", "pesë"]),
    ("Six to ten",
     ["gjashtë", "shtatë", "tetë", "nëntë", "dhjetë"]),
    ("Mum, dad, sister, brother",
     ["nënë", "baba", "babai", "mami", "babi", "motër", "vëlla"]),
    ("Boy, girl, man, woman",
     ["djalë", "vajzë", "burrë", "grua", "fëmijë", "bir"]),
    ("Bread and water",
     ["bukë", "ujë", "mish", "peshk", "djathë", "qumësht"]),
    ("Eat and drink",
     ["ha", "pi", "pije", "kafe", "verë", "birrë"]),
    ("Today, tomorrow, yesterday",
     ["sot", "nesër", "dje", "tani", "mëngjes", "natë"]),
    ("Hours, weeks, years",
     ["kohë", "orë", "javë", "muaj", "vit", "mbrëmje"]),
    ("Who, where, when, how, why",
     ["kush", "ku", "kur", "si", "pse"]),
    ("What, which, how much",
     ["farë", "çfarë", "cili", "cila", "sa"]),
    ("Do, want, go, come, say, know",
     ["bëj", "dua", "shkoj", "vij", "them", "di"]),
    ("See, speak, take, give, understand, can",
     ["shoh", "flas", "marr", "jap", "kuptoj", "mund"]),
    ("Good and bad, big and small",
     ["keq", "bukur", "madh", "vogël", "ri", "vjetër"]),
    ("Here, a lot, a little, but",
     ["këtu", "shumë", "pak", "por", "edhe", "ose"]),
    ("Home, work, friends",
     ["shtëpi", "punë", "punoj", "mik", "emër"]),
]


class OpeningError(ValueError):
    """The curated opening breaks one of the rules in the module docstring."""


def plan(levels, words, fam_of, stems_of, per_level, max_families):
    """Check `levels` against the deck and return it as [(title, [words])].

    `words` is the set of deck words, `fam_of` maps word -> family root and
    `stems_of(word)` lists the stems a word is built from. Raises
    OpeningError naming every problem, so a bad edit cannot ship quietly.
    """
    problems = []
    seen = {}
    fam_level = {}
    for i, (title, ws) in enumerate(levels, 1):
        if not title:
            problems.append("level %d has no title" % i)
        if len(ws) > per_level:
            problems.append("level %d has %d words (> %d)"
                            % (i, len(ws), per_level))
        fams = set()
        for w in ws:
            if w not in words:
                problems.append("level %d: %r is not a card in the deck"
                                % (i, w))
                continue
            if w in seen:
                problems.append("%r is listed on levels %d and %d"
                                % (w, seen[w], i))
            seen[w] = i
            f = fam_of[w]
            fams.add(f)
            if fam_level.setdefault(f, i) != i:
                problems.append("family %r is curated on levels %d and %d"
                                % (f, fam_level[f], i))
        if len(fams) > max_families:
            problems.append("level %d has %d families (> %d)"
                            % (i, len(fams), max_families))
    for w, i in seen.items():
        for s in stems_of(w):
            if s in words and seen.get(s, 10 ** 9) > i:
                problems.append("%r (level %d) is built on %r, which is "
                                "not taught by then" % (w, i, s))
    if problems:
        raise OpeningError("curated opening is invalid:\n  "
                           + "\n  ".join(problems))
    return [(title, list(ws)) for title, ws in levels]
