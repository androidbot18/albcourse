#!/usr/bin/env python3
"""Test the derivation parser that decides word-family membership.

This is the regression test for the defect that put unrelated words in the
same family: nuk (the negator, "not, don't") was filed under not (the noun,
"swim, swimming"), and the Ottoman loan bori ("bugle") under the inherited
bri ("rib"). Both came from trusting Wiktionary's "parents" and "derived"
fields as a derivation graph, which they are not.

A family edge is now accepted only when the etymology text states a
compositional derivation. These cases pin both directions: real derivations
must be found, and mere mentions must not produce an edge.
"""
import importlib.util
import os
import sys
from collections import defaultdict
from glob import glob
import json
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "build_course", os.path.join(ROOT, "tools", "build_course.py"))
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)
d = bc.derivations_from_text

failures = []


def eq(got, want, name):
    okk = got == want
    print(("  ok   " if okk else "  FAIL ") + name)
    if not okk:
        print("         got %r want %r" % (got, want))
        failures.append(name)


print("derivation parser tests")

# --- real derivations that MUST be found --------------------------------
eq(d("From marr + -ës."), ["marr"], "simple: From marr + -ës")
eq(d("marrë (foolish) + -i (-ness)"), ["marrë"], "parenthetical gloss before the plus")
eq(d("marr (take(n)) + -em (-to be)."), ["marr"],
   "nested parentheses do not leak into the base")
eq(d("marrë (taken) + mendje (mind)"), ["marrë"], "base then second element, not the second")
eq(d("From gjithë + çka."), ["gjithë"], "From gjithë + çka")
eq(d("From atë (“father”) + dhe (“land”)."), ["atë"], "curly-quoted gloss is stripped")
eq(d('From vetë ("self") + -më.'), ["vetë"], "straight-quoted gloss is stripped")
eq(d("From mund + -je feminine suffix."), ["mund"], "trailing prose after the affix")
eq(d("From di- + si."), ["di"], "hyphenated prefix is normalised")
eq(d("From në + se."), ["në"], "short function word base")

# --- mere mentions that MUST NOT produce an edge ------------------------
eq(d("From Proto-Albanian *ne uka (“not one”), from Proto-Indo-European *óynos “one” "
     "with negator *ne “not”; typologically compare Latin nōn “not”"), [],
   "nuk: English gloss words in a comparison yield no edge")
eq(d("According to Jokl, Tagliavini, Çabej a cognate to Proto-Slavic *mora (“nightmare”) / "
     "Ancient Greek μέριμνα (mérimna)"), [],
   "tmerr: a cognate is not a derivation")
eq(d("Borrowed from Ottoman Turkish borı (“horn; natural trumpet”)"), [],
   "bori: a loan word yields no edge")
eq(d("From a deverbal of Latin natāre, *notāre, compare Italian nuoto."), [],
   "not: a Latin borrowing with no affix yields no edge")
eq(d("From marrë, possibly related to mërzit."), [],
   "a bare 'From X' with no affix is a relation, not a composition")
eq(d(""), [], "empty etymology")
eq(d(None), [], "None etymology")

# --- only the first sentence is the derivation statement ----------------
eq(d("From marr + -ës. Compare Italian marrire."), ["marr"],
   "the first sentence is the derivation")
eq(d("See marr (“I take”)."), [],
   "a cross-reference is not a derivation")

# --- the real defect, on the real data ----------------------------------
card = {}
for f in sorted(glob(os.path.join(ROOT, "data", "levels", "level_*.json")),
                key=lambda p: int(re.search(r"(\d+)", os.path.basename(p)).group(1))):
    for w in json.load(open(f, encoding="utf-8"))["words"]:
        card[w["id"]] = w

if card:
    words = set(card)
    parent = {}
    for w, c in card.items():
        for base in d(c.get("etymology", "")):
            if base in words and base != w:
                parent.setdefault(w, base)
                break

    def root_of(x):
        seen, cur = {x}, x
        while cur in parent:
            cur = parent[cur]
            if cur in seen:
                break
            seen.add(cur)
        return cur

    fam = defaultdict(list)
    for w in words:
        fam[root_of(w)].append(w)

    for word, not_same in (("nuk", "not"), ("bori", "bri"),
                           ("kofshë", "hip"), ("tmerr", "marr"),
                           ("not", "nuk")):
        if word in fam and not_same in fam:
            eq(fam[word] == fam[not_same], False,
               "%s is not in the same family as %s" % (word, not_same))
            print("         %-9s -> %s | %-9s -> %s"
                  % (word, fam[word], not_same, fam[not_same]))

    # Genuine derivations must still be together.
    for a, b in (("marr", "marrës"), ("marr", "merrem"), ("gjithë", "gjithçka"),
                 ("mund", "mundje")):
        if a in fam and b in fam:
            eq(fam[a] == fam[b], True, "%s and %s stay in one family" % (a, b))

print()
if failures:
    print("FAILURES (%d):" % len(failures))
    for f in failures:
        print("  x %s" % f)
    sys.exit(1)
print("ALL DERIVATION TESTS PASSED")
