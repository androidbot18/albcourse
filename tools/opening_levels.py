"""The opening of the course, and the rules a curated level list must keep.

The opening used to be 23 hand-written levels in this file. It is now the
Conversation Core (CONVERSATION_PLAN.md): about 1,000 words and 150 phrases
ordered by situation, written in tools/core/*.txt and read by
tools/conversation_core.py. `LEVELS` below is that list, so every caller
that asks "what is curated?" gets the core.

plan() checks a curated list before the scheduler takes over:

  * every word is a card in the deck, and appears once;
  * a level holds at most `per_level` words.

For a list ordered by family (the old opening, and the unit tests that pin
these rules) it also checks:

  * a level holds at most `max_families` families;
  * a family is curated on ONE level, so it is never scattered;
  * a word's stem is taught on the same level or an earlier one.

The core is ordered by situation, so it passes `by_situation=True` and the
family rules do not apply to it: `punë`, `punoj` and `punëtor` are taught
where the conversation needs them, units apart.
"""
import conversation_core

LEVELS = conversation_core.levels()


class OpeningError(ValueError):
    """The curated opening breaks one of the rules in the module docstring."""


def plan(levels, words, fam_of, stems_of, per_level, max_families,
         by_situation=False):
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
            if by_situation:
                continue
            if fam_level.setdefault(f, i) != i:
                problems.append("family %r is curated on levels %d and %d"
                                % (f, fam_level[f], i))
        if len(fams) > max_families and not by_situation:
            problems.append("level %d has %d families (> %d)"
                            % (i, len(fams), max_families))
    for w, i in seen.items():
        if by_situation:
            break
        for s in stems_of(w):
            if s in words and seen.get(s, 10 ** 9) > i:
                problems.append("%r (level %d) is built on %r, which is "
                                "not taught by then" % (w, i, s))
    if problems:
        raise OpeningError("curated opening is invalid:\n  "
                           + "\n  ".join(problems))
    return [(title, list(ws)) for title, ws in levels]
