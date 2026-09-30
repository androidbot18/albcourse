#!/usr/bin/env python3
"""Verify the deployed site serves the rewritten form glosses (PR #15).

Cards on DELIBERATE_KEEP are excluded from the leak scan: their raw gloss
is intentional (they carry real content senses, or upstream data is poor).
"""
import json
import re
import sys
import urllib.request

URL = "https://androidbot18.github.io/albcourse/data/words.json"

# Verified individually: each keeps a real content sense or is upstream-bad data.
DELIBERATE_KEEP = {
    "të", "atë", "im", "cili", "cila", "qetë", "more",
    "kap", "mashkullor", "kënd", "moj", "muj", "neve", "dashura",
}

with urllib.request.urlopen(URL, timeout=90) as fh:
    payload = json.load(fh)

words = payload["words"] if isinstance(payload, dict) else payload
print("LIVE cards:", len(words))

scanned = [w for w in words if w["sq"] not in DELIBERATE_KEEP]
print("scanned (excl. %d deliberate keeps):" % len(DELIBERATE_KEEP), len(scanned))

checks = {
    "person-slot gloss": re.compile(r"^(third|second|first)-person\b"),
    "bare participle of X": re.compile(r"^participle of "),
    "(subjunctive) label": re.compile(r"\(subjunctive\)"),
    "(imperative of X)": re.compile(r"\(imperative of "),
    "case-slot gloss": re.compile(
        r"^(accusative|dative|nominative|genitive|vocative|ablative)\b"),
}

failed = False
for label, pattern in checks.items():
    hits = [w for w in scanned if pattern.search(w["en"].split(" (from")[0])]
    if hits:
        failed = True
    print("  %s %s: %d" % ("ok  " if not hits else "FAIL", label, len(hits)))
    for w in hits[:5]:
        print("        %s -> %s" % (w["sq"], w["en"][:70]))

# Positive control: the rewrite must actually be present.
sample = [w for w in words if w["en"].startswith("he/she/it is (from jam")]
if not sample:
    failed = True
print("  %s rewrite present: %d card(s)" % (
    "ok  " if sample else "FAIL", len(sample)))

# The deliberate keeps must survive the merge intact.
keeps = [w["sq"] for w in words if w["sq"] in DELIBERATE_KEEP]
if len(keeps) != len(DELIBERATE_KEEP):
    failed = True
print("  %s deliberate keeps intact: %d/%d" % (
    "ok  " if len(keeps) == len(DELIBERATE_KEEP) else "FAIL",
    len(keeps), len(DELIBERATE_KEEP)))

print("LIVE GLOSS CHECK PASSED" if not failed else "LIVE GLOSS CHECK FAILED")
sys.exit(1 if failed else 0)
