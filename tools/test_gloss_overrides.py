"""The reviewed headline-gloss fixes (section 4.1) reach the shipped deck.

Run as:  python3 tools/test_gloss_overrides.py

Pins each override in tools/gloss_overrides.py against data/words.json, and
checks that no card headlines Wiktionary's raw head line ("errësirë f
(plural ...") instead of a meaning. The control proves the junk pattern
does match the defect it was written for.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gloss_overrides as go  # noqa: E402

failures = []


def check(name, ok):
    print("  %s %s" % ("ok  " if ok else "FAIL", name))
    if not ok:
        failures.append(name)


with open(os.path.join(os.path.dirname(HERE), "data", "words.json"),
          encoding="utf-8") as fh:
    W = {w["sq"]: w for w in json.load(fh)["words"]}

for w, glosses in go.FRONT.items():
    check("%s headlines %r (got %r)" % (w, glosses[0], W[w]["en"]),
          W[w]["en"] == glosses[0])
for w, (_, gloss) in go.REPLACE.items():
    check("%s headlines %r" % (w, gloss), W[w]["en"] == gloss)

by_sense = {}
for w in set(go.RENAME) | set(go.ADD):
    by_sense[w] = [x for L in glob.glob(os.path.join(
        os.path.dirname(HERE), "data", "levels", "level_*.json"))
        for c in json.load(open(L, encoding="utf-8"))["words"] if c["sq"] == w
        for x in [s["gloss"] for s in c["sense_detail"]]]
for w, ren in go.RENAME.items():
    for old, new in ren.items():
        check("%s: %r is %s" % (w, old[:30], "dropped" if new is None
                                else "now %r" % new[:30]),
              old not in by_sense[w] and (new is None or new in by_sense[w]))
for w, (at, _, gloss) in go.ADD.items():
    check("%s: sense %d is %r" % (w, at, gloss),
          by_sense[w][at:at + 1] == [gloss])
for w, (_, sq, en) in go.EXAMPLES.items():
    check("%s shows the reviewed example %r" % (w, sq),
          (W[w].get("ex") or {}).get("sq") == sq)

junk = sorted(w for w, c in W.items() if go.HEADLINE_JUNK.match(c["en"]))
check("no card headlines a raw dictionary head line (got %s)" % junk[:5],
      not junk)
check("control: the pattern matches the defect",
      bool(go.HEADLINE_JUNK.match("errësirë f (plural errësirë, definite errësira)")))
check("control: the pattern spares a real gloss",
      not go.HEADLINE_JUNK.match("calf; cattle (offspring of a cow)"))

print()
if failures:
    print("FAILURES (%d)" % len(failures))
    sys.exit(1)
print("ALL GLOSS-OVERRIDE CHECKS PASSED")
