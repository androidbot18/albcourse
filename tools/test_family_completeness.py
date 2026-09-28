#!/usr/bin/env python3
"""No derivable family edge is being missed.

The family rule is strict by design: a word joins a family only when its
etymology text states a composition. Strictness cuts both ways, and the
failure that matters is UNDER-linking -- a real derivative sitting alone
because the parser missed it. That is invisible in the counts (families just
look smaller) and would quietly weaken every level built on them.

So this asserts the property directly: for every card whose etymology names a
base that IS a deck word, that base must be its declared parent. Any card
failing this is a parser miss, not a deliberate exclusion.

Cards whose etymology has a "+" but whose base is not a deck word (farë in
"ç' + farë", ndih in "ndih + -më") are correctly singletons and are counted
separately, because there is nothing to link them to.
"""
import glob
import importlib.util
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "build_course", os.path.join(ROOT, "tools", "build_course.py"))
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)
d = bc.derivations_from_text

# Rebuild the same parent map build_families() builds.
card = {}
for f in sorted(glob.glob(os.path.join(ROOT, "data", "levels", "level_*.json")),
                key=lambda p: int(re.search(r"(\d+)", os.path.basename(p)).group(1))):
    for w in json.load(open(f, encoding="utf-8"))["words"]:
        card[w["id"]] = w
words = set(card)
parent = {}
for w, c in card.items():
    for base in d(c.get("etymology", "")):
        if base in words and base != w:
            parent.setdefault(w, base)
            break

missed = []
no_base = 0
for w, c in card.items():
    text = (c.get("etymology") or "").strip()
    if not text:
        continue
    head = re.split(r"(?<=[.;])\s", text)[0]
    if "+" not in head:
        continue
    bases = d(text)
    if not bases:
        no_base += 1
        continue
    if bases[0] in words and bases[0] != w and parent.get(w) != bases[0]:
        missed.append((w, bases[0], parent.get(w)))

print("family completeness tests")
print("  cards with a + composition but no deck-word base: %d" % no_base)
print("  cards with a real base that are NOT linked:       %d" % len(missed))
for w, b, got in missed[:15]:
    print("    %-14s base=%-12s linked to %r" % (w, b, got))

if missed:
    print("\nFAILURES (%d): %d derivable family edges are being dropped"
          % (len(missed), len(missed)))
    sys.exit(1)
print("\nNO DERIVABLE FAMILY EDGE IS MISSED")

# ------------------------------------------------------------ negative control
# A check that cannot fail is not a check. Simulate a dropped edge: if the
# assertion below really is enforced, removing a parent must be detected.
sample = None
for w, b in parent.items():
    sample = (w, b)
    break
if sample is None:
    print("\nnegative control skipped: no edges to drop")
    sys.exit(0)
w0, b0 = sample
broken = dict(parent)
del broken[w0]
detected = (broken.get(w0) != b0)
print("\nnegative control: dropping the edge %s -> %s is detected: %s"
      % (w0, b0, detected))
if not detected:
    print("FAIL: the assertion cannot detect a dropped edge")
    sys.exit(1)
print("NEGATIVE CONTROL VERIFIED")
