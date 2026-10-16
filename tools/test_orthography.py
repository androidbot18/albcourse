"""Orthography gate: no shipped example is misspelt Albanian.

Run as:  python3 tools/test_orthography.py

Section 4.2 of RECOMMENDATIONS.md found examples written without ë ("Ai
eshte ..."), with a Lithuanian ė ("Do jesh mirė"), and Wiktionary quotes in
pre-standard historical spelling. tools/orthography.py now rejects them at
build time. This pins the gate on hand-written sentences, with controls
that real words such as te, ne and veten still pass, and checks every
example the shipped deck can show.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import orthography  # noqa: E402

DATA = os.path.join(os.path.dirname(HERE), "data")
failures = []


def check(name, ok):
    print("  %s %s" % ("ok  " if ok else "FAIL", name))
    if not ok:
        failures.append(name)


print("== the gate on hand-written sentences ==")
# A tiny dictionary and ranking, shaped like the real ones.
known = {"është", "një", "këtu", "mirë", "te", "ne", "qe", "veten", "vetën",
         "ai", "libër", "jam", "nuk", "do", "paqe", "rrimë"}
rank = {"është": 6, "një": 11, "këtu": 38, "mirë": 21, "te": 22, "ne": 29,
        "qe": 83, "veten": 223, "vetën": 2274, "ketu": 234, "rrime": 21478,
        "rrimë": 1957}
g = orthography.Gate(known, rank)

check("standard spelling passes", g.ok("Ai është një libër."))
check("eshte/nje without ë is rejected", not g.ok("Ai eshte nje libër."))
check("the fix offered is the ë-spelling",
      g.problems("Ai eshte këtu.") == ["eshte for është"])
check("ketu (5x rarer than këtu) is rejected", not g.ok("Jam ketu."))
check("Lithuanian ė is rejected", not g.ok("Do jesh mirė."))
check("historical spelling is rejected", not g.ok("CHeio anſte ieta"))
check("w (not an Albanian letter) is rejected", not g.ok("Policia e përbuz Waze."))
check("Greek script is rejected", not g.ok("dόλλι τρε̰νdαφύλι"))
# Controls: real words without ë must not be caught.
check("control: te, ne and qe are words, not typos", g.ok("Ne jemi te ai qe."))
check("control: veten outranks vetën, so it passes", g.ok("Nuk pyet për veten."))
check("control: a card may show its own headword",
      g.ok("Nuk do rrime.", headword="rrime") and not g.ok("Nuk do rrime."))
check("control: a reviewed known word passes", g.ok("rroba banje"))

print("\n== shipped deck ==")
TOK = re.compile(r"[^\W\d_]+")
files = sorted(glob.glob(os.path.join(DATA, "levels", "level_*.json")))
if not files:
    print("  skip data/levels not built")
else:
    shown = []  # (word, sentence) for every example a card can show
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for w in json.load(fh)["words"]:
                for s in w.get("sense_detail") or []:
                    for e in s.get("examples") or []:
                        shown.append((w["sq"], e["sq"]))
                if w.get("corpus_example"):
                    shown.append((w["sq"], w["corpus_example"]["sq"]))
    with open(os.path.join(DATA, "words.json"), encoding="utf-8") as fh:
        for w in json.load(fh)["words"]:
            if w.get("ex"):
                shown.append((w["sq"], w["ex"]["sq"]))
    foreign = [(w, s) for w, s in shown if orthography.foreign_letters(s)]
    check("every example uses only Albanian letters (%d of %d do not: %s)"
          % (len(foreign), len(shown), foreign[:3]), not foreign)
    typos = [(w, s) for w, s in shown
             if any(t.lower() in orthography.COMMON_TYPOS
                    for t in TOK.findall(s) if t.lower() != w.lower())]
    check("no example has a common ë-less typo (%d: %s)" % (len(typos), typos[:3]),
          not typos)
    with open(os.path.join(DATA, "report.json"), encoding="utf-8") as fh:
        rej = json.load(fh).get("orthography_rejected") or {}
    check("the build reports what the gate rejected (%s)" % rej,
          rej.get("wiktionary", 0) > 0 and rej.get("corpus", 0) > 0)

print()
if failures:
    print("FAILURES (%d):" % len(failures))
    for f in failures:
        print("  x " + f)
    sys.exit(1)
print("ALL ORTHOGRAPHY CHECKS PASSED")
