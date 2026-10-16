"""The main course and the extended track (RECOMMENDATIONS.md section 3.6).

Run as:  python3 tools/test_scope.py

The main course is the words ranked up to build_course.MAIN_MAX_RANK, the
curated opening, and the stems those words are built on. Everything else is
an optional extended track after it. Pins:

  * schedule_course() puts each card in the right track, pulls a rare stem
    into the main course when a main word is built on it, and drops nothing;
  * the shipped data marks the split consistently in the level files,
    course.json, index.json and words.json;
  * the main course stays small (MAIN_CEILING levels) and still reaches 80%
    of running text, counting a token as known when it is a card or an
    inflected form Wiktionary lists for one. That is the goal the cut was
    made for, so it is measured rather than assumed.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_course as bc  # noqa: E402
import opening_levels as ol  # noqa: E402

ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
MAIN_CEILING = 360
COVERAGE_GOAL = 0.80
failures = []


def check(name, ok):
    print("  %s %s" % ("ok  " if ok else "FAIL", name))
    if not ok:
        failures.append(name)


print("== schedule_course() on a synthetic course ==")


def card(word, rank):
    return {"word": word, "rank": rank,
            "senses": [{"pos": "adv", "pos_label": "adverb",
                        "gloss": word, "tags": []}]}


cards = [card("a", 10), card("ab", 20), card("abz", 9000), card("z", 8000),
         card("rare", 7000), card("cur", 6000)]
families = {"a": ["a", "ab", "abz"], "z": ["z"], "rare": ["rare"],
            "cur": ["cur"]}
# ab is built on z: z is rare, but a main-course word needs it.
components = {"ab": [{"word": "z", "role": "stem"}]}
levels = bc.schedule_course(cards, families, components=components,
                            opening=[("Curated", ["cur"])],
                            main_max_rank=100)
lv = {w: i for i, L in enumerate(levels, 1) for w in L[1]}
ext = {w for L in levels if L[7].get("extended") for w in L[1]}
check("nothing is dropped", sorted(lv) == sorted(c["word"] for c in cards))
check("a curated word is main course whatever its rank", "cur" not in ext)
check("a rare stem of a main word is pulled into the main course",
      "z" not in ext and lv["z"] <= lv["ab"])
check("words above the cap are extended", ext == {"abz", "rare"})
flags = [bool(L[7].get("extended")) for L in levels]
check("the extended track follows the main course",
      flags == sorted(flags))
more = [L for L in levels if "abz" in L[1]]
check("a family the main course began comes back as '(more)' (got %r)"
      % (more[0][2] if more else None),
      more and "a (more)" in more[0][2])
whole = bc.schedule_course(cards, families, components=components,
                           opening=[("Curated", ["cur"])],
                           main_max_rank=10 ** 9)
check("control: with no cap there is no extended track",
      not any(L[7].get("extended") for L in whole))


print("\n== shipped data ==")
files = sorted(glob.glob(os.path.join(DATA, "levels", "level_*.json")),
               key=lambda f: int(re.search(r"(\d+)\.json$", f).group(1)))
shipped = [json.load(open(f, encoding="utf-8")) for f in files]
if not shipped:
    print("  skip data/levels not built")
else:
    course = json.load(open(os.path.join(DATA, "course.json"),
                            encoding="utf-8"))
    index = json.load(open(os.path.join(DATA, "index.json"),
                           encoding="utf-8"))
    words = json.load(open(os.path.join(DATA, "words.json"),
                           encoding="utf-8"))["words"]
    main = [L for L in shipped if not L.get("extended")]
    n_main = len(main)
    check("the main course is %d levels, within %d"
          % (n_main, MAIN_CEILING), n_main <= MAIN_CEILING)
    check("the extended track is a suffix of the course",
          all(not L.get("extended") for L in shipped[:n_main])
          and all(L.get("extended") for L in shipped[n_main:]))
    check("course.json main_level_count agrees",
          course.get("main_level_count") == n_main)
    check("index.json marks the same levels",
          [bool(x.get("extended")) for x in index]
          == [bool(L.get("extended")) for L in shipped])
    ext_words = {w["sq"] for L in shipped[n_main:] for w in L["words"]}
    check("words.json marks the same words",
          {w["sq"] for w in words if w.get("extended")} == ext_words)

    curated = {w for _, ws in ol.LEVELS for w in ws}
    main_words = {w["sq"]: w for L in main for w in L["words"]}
    stems = {c["word"] for w in main_words.values()
             for c in w.get("components") or [] if c.get("role") == "stem"}
    stray = sorted(w for w, c in main_words.items()
                   if c["rank"] > bc.MAIN_MAX_RANK
                   and w not in curated and w not in stems)
    check("every main word is within rank %d, curated, or a stem (%s)"
          % (bc.MAIN_MAX_RANK, stray[:5]), not stray)
    low = sorted(w["sq"] for L in shipped[n_main:] for w in L["words"]
                 if w["rank"] <= bc.MAIN_MAX_RANK)
    check("no extended word is within rank %d (%s)"
          % (bc.MAIN_MAX_RANK, low[:5]), not low)

    # Coverage of the frequency list's tokens by the main course.
    freq_path = os.path.join(DATA, "raw", "sq_50k.txt")
    dict_path = os.path.join(DATA, "raw", "kaikki_albanian.jsonl")
    if not (os.path.exists(freq_path) and os.path.exists(dict_path)):
        print("  skip coverage: data/raw not present")
    else:
        import measure_coverage as mc
        count = mc.frequency_counts(freq_path)
        lemmas_of = mc.lemma_index(dict_path)
        known = set(main_words)

        def covered(deck):
            return mc.coverage(deck, count, lemmas_of)

        share = covered(known)
        check("the main course covers %.1f%% of tokens (goal %.0f%%)"
              % (100 * share, 100 * COVERAGE_GOAL), share >= COVERAGE_GOAL)
        everything = {w["sq"] for w in words}
        print("  info whole course, extended track included: %.1f%%"
              % (100 * covered(everything)))

print()
if failures:
    print("FAILURES (%d):" % len(failures))
    for f in failures:
        print("  x " + f)
    sys.exit(1)
print("ALL SCOPE CHECKS PASSED")
