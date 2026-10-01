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

# --- derivations stated in a LATER sentence must still be found -----------
# esëll's etymology only names its base in the third sentence. A
# first-sentence-only rule split it from its root e, which is a real family
# broken by the strictness of the rule, not a deliberate exclusion.
eq(d("From Proto-Albanian *a-tšilna, a compound equivalent to a privative e- + "
     "sillë (“breakfast”). Interpretible as e- + sille (“breakfast”)."), ["e"],
   "esëll: base named in a later sentence still counts")
eq(d("From Old Albanian vdekëlë, derivative built from vdekur, past participle of "
     "vdes; vdes + -je."), ["vdes"], "vdekje: after a semicolon")
eq(d("Gerund of ushqej (“to feed”); ushqej + -im."), ["ushqej"],
   "ushqim: a bare second sentence")

# --- a comparison is NOT a derivation, however the + is placed ------------
# This is the original nuk/not defect. The aside describes LATIN, not Albanian:
#   "typologically compare Latin nōn (“not”), noenum (“idem”) (< ne + ūnus)"
eq(d("From Proto-Albanian *ne uka (“not one”) with negator *ne (“not”); "
     "typologically compare Latin nōn (“not”), noenum (“(Old Latin) idem”) "
     "(< ne + ūnus ~ ūnum)."), [],
   "nuk: a Latin comparison aside is not a derivation")
eq(d("From Proto-Albanian *apsera, perhaps a contamination of *aps. "
     "Cognates include Latin adsim, Greek ἄψ. Alternatively, from a + -fër."),
   ["a"], "an explicit alternative derivation after a cognate list still counts")

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



# --- components_of: a joiner is not a stem -------------------------------
# gjëegjëzë is gjë + e + gjëzë, where e is the conjunctive "and" sitting
# between two lexical elements. It is not a base the learner needs first,
# so it must not become a stem. The two-part nëse = në + se keeps se,
# because there se really is the word that has to be known first.
W = {"gjë", "e", "gjëzë", "në", "se", "do", "mos", "me",
     "thënë", "së", "mund", "pa", "besë", "sillë", "dritë"}

for text, want_stem, why in [
    ("From gjë + e + gjëzë.", None,
     "e between two words in a compound is a joiner"),
    ("From do + e + mos.", None,
     "e between do and mos is a joiner"),
    ("Univerbation of do + me + thënë.", None,
     "me between do and thënë is a joiner"),
    ("From në + se.", "se",
     "two-part nëse keeps its real stem"),
    ("e- + sillë", "sillë",
     "the headline case esëll = e- + sillë keeps sillë"),
    ("From së- + mund + -je.", "mund",
     "a base before a hyphenated suffix is still the stem"),
    ("From pa- + besë + -ë.", "besë",
     "three-part pabesë keeps besë"),
]:
    got = bc.components_of(text, W)
    stems = [w for w, role in got if role == "stem"]
    eq(stems, [want_stem] if want_stem else [], why)

# Negative control: the joiner rule must not be the reason the headline
# case works, since esëll is two parts and never hits the rule.
eq(bc.components_of("e- + sillë", W) != [], True,
   "esëll still resolves components at all")


# --- the stem side ends at its own clause ------------------------------
# kush reads "...Proto-Indo-European *kʷos + *sos, meaning 'who (is) this'".
# The "+" joins two RECONSTRUCTED forms, but _side_word() matched the spelling
# "sos" against the deck word sos ("indeed"), inventing an edge that held ai
# (rank 35) back to L614 behind a rank-19473 word. Prose is not a composition.
# kruaj must be in the word set: a stem the course does not teach is
# correctly rejected as "not a deck word", which would mask this rule.
PROSE_W = W | {"sos", "kurrë", "ne", "kush", "kruaj", "rravsh"}

for text, want_stem, why in [
    ('From Proto-Indo-European *kʷos + *sos, meaning "who (is) this".', None,
     "a reconstructed PIE form is not a stem the learner must know"),
    ("Compound of Proto-Albanian *kur + *ne/o- negative particle.", None,
     "a starred affix + starred base is prose, not a lesson prerequisite"),
    ("From Proto-Albanian *(V)(m)pi, from *h₂en-h₁pi + *h₁(é)pi.", None,
     "reconstruction inside the stem side yields no stem"),
    # The other side of the same rule: a base that merely sits after the
    # comma is in the NEXT clause, so it is not this word's stem either.
    ("From a compound *rravsh + -oj, the first element of which is borrowed.", None,
     "a word named after the comma is in another clause"),
    # Negative controls: real compositions, none of which has a clause
    # break or a star between the "+" and its base.
    ("From e- + sillë.", "sillë",
     "esëll = e- + sillë keeps its real stem"),
    ("* From sh- (\u201coff\u201d) + kruaj (\u201cto scratch\u201d) q.v.;", "kruaj",
     "shkruaj = sh- + kruaj keeps kruaj"),
]:
    got = bc.components_of(text, PROSE_W)
    stems = [w for w, role in got if role == "stem"]
    eq(stems, [want_stem] if want_stem else [], why)

# The defect itself, as an end-to-end guard on the built deck: ai and kush
# are among the 100 commonest words, so neither may sit past level 100.
try:
    import json as _json
    import os as _os
    here = _os.path.dirname(_os.path.abspath(__file__))
    _idx = _json.load(open(_os.path.join(here, "..", "data", "index.json")))
    _pos = {}
    for _lv in _idx:
        _f = _os.path.join(here, "..", "data", "levels",
                           "level_%03d.json" % _lv["level"])
        for _c in _json.load(open(_f))["words"]:
            _pos[_c["sq"]] = _lv["level"]
    for _w in ("ai", "kush"):
        if _w in _pos:
            eq(_pos[_w] <= 100, True,
               "%s is taught in the opening, not held behind a rare stem" % _w)
except (IOError, OSError, ValueError):
    pass

print()
if failures:
    print("FAILURES (%d):" % len(failures))
    for f in failures:
        print("  x %s" % f)
    sys.exit(1)
print("ALL DERIVATION TESTS PASSED")
