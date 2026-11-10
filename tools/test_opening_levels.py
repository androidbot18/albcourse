"""The hand-curated opening (RECOMMENDATIONS.md section 3.2).

Run as:  python3 tools/test_opening_levels.py

Pins three things:

  * plan() refuses a curated list that breaks a rule (a word not in the
    deck, a family on two levels, a stem taught after its word, an
    oversized level). Each rule has a negative control, because a check
    that cannot fail would let a bad edit ship.
  * assign_levels() puts the curated levels first, exactly as written, and
    brings back the rest of a partly curated family later, on a level that
    says so (`continues`). Nothing is dropped.
  * The shipped deck opens with tools/opening_levels.LEVELS, and the
    words a learner meets first have reviewed glosses (`pi` is "to drink",
    not the Gheg preposition "from").
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

LEVELS = os.path.join(os.path.dirname(HERE), "data", "levels")
failures = []


def check(name, ok):
    print("  %s %s" % ("ok  " if ok else "FAIL", name))
    if not ok:
        failures.append(name)


def refuses(levels, words, fam_of, stems=None, why=""):
    stems = stems or {}
    try:
        ol.plan(levels, words, fam_of, lambda w: stems.get(w, []), 9, 6)
    except ol.OpeningError as e:
        return why in str(e)
    return False


print("== plan() rules, each with a negative control ==")
W = {"a", "ab", "b", "c", "d"}
F = {"a": "a", "ab": "a", "b": "b", "c": "c", "d": "d"}
good = [("one", ["a", "b"]), ("two", ["c"])]
check("a valid plan is accepted",
      ol.plan(good, W, F, lambda w: [], 9, 6) == good)
check("a word not in the deck is refused",
      refuses([("one", ["a", "zz"])], W, F, why="not a card"))
check("a word listed twice is refused",
      refuses([("one", ["a"]), ("two", ["a"])], W, F, why="listed on levels"))
check("a family on two levels is refused",
      refuses([("one", ["a"]), ("two", ["ab"])], W, F,
              why="curated on levels"))
check("a stem curated after its word is refused",
      refuses([("one", ["ab"]), ("two", ["b"])], W, F, {"ab": ["b"]},
              why="not taught by then"))
check("a stem left out of the opening is refused",
      refuses([("one", ["ab"])], W, F, {"ab": ["b"]},
              why="not taught by then"))
check("a stem on the same level is accepted",
      not refuses([("one", ["b", "ab"])], W, F, {"ab": ["b"]}))
check("a level over 9 words is refused",
      refuses([("one", ["a"] + ["x%d" % i for i in range(9)])],
              W | {"x%d" % i for i in range(9)},
              dict(F, **{"x%d" % i: "x%d" % i for i in range(9)}),
              why="words (> 9)"))
check("a level over 6 families is refused",
      refuses([("one", ["x%d" % i for i in range(7)])],
              {"x%d" % i for i in range(7)},
              {"x%d" % i: "x%d" % i for i in range(7)},
              why="families (> 6)"))
check("the shipped list passes its own rules",
      all(len(ws) <= 9 for _, ws in ol.LEVELS))


print("\n== assign_levels() on a synthetic course ==")


def card(word, rank):
    return {"word": word, "rank": rank,
            "senses": [{"pos": "adv", "pos_label": "adverb",
                        "gloss": word, "tags": []}]}


cards = [card("r", 50), card("r1", 51), card("r2", 52), card("q", 60)]
families = {"r": ["r", "r1", "r2"], "q": ["q"]}
for i in range(30):
    cards.append(card("s%02d" % i, i + 1))
    families["s%02d" % i] = ["s%02d" % i]
opening = [("Theme", ["r", "q"])]
levels = bc.assign_levels(cards, families, opening=opening)
lv = {w: i for i, L in enumerate(levels, 1) for w in L[1]}
check("the curated level is level 1", sorted(levels[0][1]) == ["q", "r"])
check("it keeps its title and is marked", levels[0][2] == "Theme"
      and levels[0][7].get("opening") is True)
check("nothing is dropped", sorted(lv) == sorted(c["word"] for c in cards))
check("each word is taught once", sum(len(L[1]) for L in levels) == len(cards))
back = levels[lv["r1"] - 1]
check("the rest of a curated family comes back later", lv["r1"] > 1)
check("and the level that brings it back says so",
      back[7].get("continues") == ["r"])
check("it is titled as a continuation", back[2] == "r (continued)")
check("a fully curated family does not come back",
      not any("q" in L[7].get("continues", []) for L in levels))
plain = bc.assign_levels(cards, families)
check("control: without the opening, the course opens by frequency",
      plain[0][1][0] == "s00" and not plain[0][7])


print("\n== shipped deck ==")
files = sorted(glob.glob(os.path.join(LEVELS, "level_*.json")),
               key=lambda f: int(re.search(r"(\d+)\.json$", f).group(1)))
shipped = [json.load(open(f, encoding="utf-8")) for f in files]
if not shipped:
    print("  skip data/levels not built")
else:
    n = len(ol.LEVELS)
    # In order, not merely the same set: a core example may use the word
    # taught just before it on the same level.
    check("the first %d levels are the curated ones, in order" % n,
          [(L["title"], [w["sq"] for w in L["words"]]) for L in shipped[:n]]
          == [(t, list(ws)) for t, ws in ol.LEVELS])
    check("they are marked `opening`, and no other level is",
          all(L.get("opening") for L in shipped[:n])
          and not any(L.get("opening") for L in shipped[n:]))

    lvl_of = {w["sq"]: L["level"] for L in shipped for w in L["words"]}
    fam_of = {w["sq"]: w["family"] for L in shipped for w in L["words"]}
    curated = {w for _, ws in ol.LEVELS for w in ws}
    # The main course brings a curated family back marked `continues`; its
    # rarer members may instead wait for the extended track, which says
    # "(more)" (build_course.schedule_course).
    main_words = {w["sq"] for L in shipped if not L.get("extended")
                  for w in L["words"]}
    partial = {fam_of[w] for w in curated} & {
        fam_of[w] for w in main_words if w not in curated}
    first_back = {}
    for L in shipped[n:]:
        if L.get("extended"):
            continue
        for f in L["families"]:
            first_back.setdefault(f, L)
    missing = sorted(f for f in partial
                     if f not in (first_back[f].get("continues") or []))
    check("every partly curated family comes back marked `continues` "
          "(%d families; unmarked: %s)" % (len(partial), missing[:5]),
          not missing)
    stray = sorted({f for L in shipped for f in (L.get("continues") or [])}
                   - partial)
    check("`continues` names only families the opening began (%s)"
          % stray[:5], not stray)

    # What a learner meets first. The bounds are unit boundaries of the
    # Conversation Core: greetings by L6, politeness by L22, the cafe by
    # L58, the days of the week by L90, the family by L98.
    for w, by in (("përshëndetje", 1), ("po", 1), ("jo", 1),
                  ("faleminderit", 1), ("unë", 3), ("jam", 3), ("një", 9),
                  ("kafe", 9), ("ujë", 9), ("kam", 12), ("çfarë", 22),
                  ("sot", 31), ("dhjetë", 45), ("bukë", 58), ("hënë", 90),
                  ("diel", 90), ("nënë", 98)):
        check("%s is taught by L%d (L%s)" % (w, by, lvl_of.get(w)),
              lvl_of.get(w, 10 ** 9) <= by)

    # One card per word (CONVERSATION_PLAN.md step 2): a paradigm is a
    # line on its word's card, not a run of cards.
    card_of = {w["sq"]: w for L in shipped for w in L["words"]}
    for form in ("është", "jemi", "ishte", "kemi", "shkon"):
        check("%s is not a card of its own" % form, form not in card_of)
    check("the jam card shows its present tense",
          card_of["jam"].get("forms_line")
          == "jam · je · është · jemi · jeni · janë")
    check("a verb card shows its key forms (shkoj: %r)"
          % card_of["shkoj"].get("forms_line"),
          card_of["shkoj"].get("forms_line")
          == "ai shkon · shkova (past) · kam shkuar")
    check("a noun card shows its definite and plural (djalë: %r)"
          % card_of["djalë"].get("forms_line"),
          card_of["djalë"].get("forms_line") == "djali · pl. djem")
    check("an adjective card shows its linking article (mirë: %r)"
          % card_of["mirë"].get("forms_line"),
          card_of["mirë"].get("forms_line") == "i mirë · e mirë")
    check("the folded forms are listed on the word (shkoj has shkon)",
          "shkon" in {f["form"] for f in card_of["shkoj"]["forms"]})

    for w, gloss in (("pi", "to drink"), ("kafe", "coffee"),
                     ("qumësht", "milk"), ("njeri", "person, man"),
                     ("pas", "after; behind"), ("pres", "to wait")):
        check("%s headlines %r (got %r)" % (w, gloss, card_of[w]["en"]),
              card_of[w]["en"] == gloss)
    days = (("hënë", "Monday"), ("martë", "Tuesday"),
            ("mërkurë", "Wednesday"), ("enjte", "Thursday"),
            ("premte", "Friday"), ("shtunë", "Saturday"),
            ("diel", "Sunday"))
    for w, day in days:
        check("%s is a card headlined %s, showing its article (got %r, %r)"
              % (w, day, card_of.get(w, {}).get("en"),
                 card_of.get(w, {}).get("forms_line")),
              (card_of.get(w, {}).get("en") or "").startswith(day)
              and (card_of.get(w, {}).get("forms_line") or "").startswith(
                  "e %s" % w))
    check("pi's example is the core's own, not 'A pi drogë?'",
          card_of["pi"]["sense_detail"][0]["examples"][0]["sq"]
          == "Unë pi vetëm ujë."
          and not card_of["pi"].get("corpus_example"))
    check("no core card falls back to a corpus sentence",
          not [w for w in curated if card_of[w].get("corpus_example")])
    check("e- words are not in the family of e ('and')",
          card_of["esëll"]["family"] != "e")

print()
if failures:
    print("FAILURES (%d):" % len(failures))
    for f in failures:
        print("  x " + f)
    sys.exit(1)
print("ALL CURATED-OPENING CHECKS PASSED")
