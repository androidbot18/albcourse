"""Affix patterns and breakdowns: what the learner is told about word parts.

Run as:  python3 tools/test_affixes.py

The roots idea only helps if what it shows is true. These pin the rules in
tools/affixes.py against the shipped level files:

  * a breakdown comes from the etymology, never from spelling;
  * "transparent" (offered as guess-from-the-parts) only for reviewed words
    whose every affix is taught;
  * a historical breakdown never shows a stem gloss (they are often the
    wrong homograph: pije is pi "to drink", the deck's pi card is "from");
  * the -im noun suffix is never confused with the -im "we" verb ending;
  * a pattern lands on the level of its third clear example;
  * the shipped files are what affixes.py produces (so editing the
    catalogue without re-running it fails here, not on the live site).
"""
import copy
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import affixes  # noqa: E402

LEVELS = os.path.join(os.path.dirname(HERE), "data", "levels")

failures = []


def eq(got, want, why):
    if got == want:
        print("  ok   %s" % why)
    else:
        print("  FAIL %s\n         got  %r\n         want %r" % (why, got, want))
        failures.append(why)


def load():
    levels = []
    for f in glob.glob(os.path.join(LEVELS, "level_*.json")):
        with open(f, encoding="utf-8") as fh:
            levels.append(json.load(fh))
    levels.sort(key=lambda l: l["level"])
    return levels


levels = load()
cards = [w for l in levels for w in l["words"]]
by_sq = {w["sq"]: w for w in cards}
transparent = [w for w in cards if w.get("breakdown") == "transparent"]
historical = [w for w in cards if w.get("breakdown") == "historical"]
print("cards: %d  transparent: %d  historical: %d"
      % (len(cards), len(transparent), len(historical)))

print("breakdowns come from the etymology")
no_eq = [w["sq"] for w in cards
         if w.get("components") and "+" not in (w.get("etymology") or "")]
eq(no_eq, [], "every breakdown has a '+' equation in its etymology")
# Negative control for the rule above: spelling would split shkollë into
# sh- + kollë ("cough"). The parser must not.
eq((by_sq.get("shkollë") or {}).get("components") or [], [],
   "shkollë is not sh- + kollë")
eq([w["sq"] for w in cards if w.get("components") and not w.get("breakdown")],
   [], "every card with components is classified")

print("transparent means reviewed and fully taught")
eq(sorted(w["sq"] for w in transparent if w["sq"] not in affixes.TRANSPARENT),
   [], "only reviewed words are transparent")
untaught = [w["sq"] for w in transparent
            for c in w["components"]
            if c["role"] in ("prefix", "suffix") and not c.get("affix")
            and c["word"] not in affixes.NEUTRAL_SUFFIXES]
eq(untaught, [], "a transparent breakdown uses only taught affixes")
eq(by_sq["përdor"]["breakdown"], "historical",
   "përdor (për- + dorë 'hand' = use) is historical")
eq(by_sq["mundësi"]["breakdown"], "transparent",
   "mundësi (mund + -ësi = possibility) is transparent")

print("historical breakdowns carry no stem gloss")
leaked = [w["sq"] for w in historical for c in w["components"] if c.get("en")]
eq(leaked, [], "no stem gloss on a historical breakdown")
eq([c.get("en") for c in by_sq["pije"]["components"]], [None, None],
   "pije does not show pi as 'from'")

print("-im the noun is not -im the verb ending")
we = [w["sq"] for w in transparent
      if any(c.get("affix") == "im" for c in w["components"])
      and w["en"].lower().startswith("we ")]
eq(we, [], "no 'we ...' verb form is a transparent -im noun")
# The collision is real, which is why the note exists: flasim is in the deck.
eq("flasim" in by_sq and not by_sq["flasim"].get("components"), True,
   "flasim ('we speak') exists and carries no -im breakdown")
eq("flasim" in affixes.AFFIXES["im"]["note"], True,
   "the -im pattern note warns about the verb ending")

print("patterns")
placed = {}
for l in levels:
    for p in l.get("patterns") or []:
        placed[p["id"]] = l["level"]
for aid, lv in sorted(placed.items()):
    first = []
    for l in levels:
        for w in l["words"]:
            if w in transparent and any(c.get("affix") == aid
                                        for c in w["components"]):
                first.append(l["level"])
    eq(lv, first[affixes.MIN_EXAMPLES - 1],
       "%s lands on the level of its 3rd clear example" % aid)
eq(set(placed) <= set(affixes.AFFIXES), True, "every pattern is catalogued")
eq("zh" in placed, False,
   "zh- (2 clear examples in this deck) is not taught as a pattern")

print("shipped data matches affixes.py")
fresh = copy.deepcopy(levels)
affixes.annotate_levels(fresh)
eq(fresh == levels, True,
   "re-running annotate_levels changes nothing (run tools/affixes.py)")
# Negative control: the comparison above must be able to fail.
broken = copy.deepcopy(levels)
for w in broken[0]["words"]:
    w["breakdown"] = "transparent"
eq(broken == fresh, False, "negative control: a tampered level is detected")

print()
if failures:
    print("FAILURES (%d):" % len(failures))
    for f in failures:
        print("  x %s" % f)
    sys.exit(1)
print("ALL AFFIX TESTS PASSED")
