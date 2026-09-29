#!/usr/bin/env python3
"""How many selected examples are actually software/plural path fragments?

HPLT is a wiki corpus, so it contains file paths, command lines and technical
identifiers. A word can satisfy a token match without the sentence teaching
the word: 'fil' inside 'cpuinfo-fil' is the giveaway, and the same class covers
unrelated proper nouns that merely contain a deck word.
"""
import json, re
from pathlib import Path

new = json.loads(Path("corpus_examples.json").read_text())
deck = {w["sq"]: w for w in json.loads(Path("albcourse/data/words.json").read_text())["words"]}

TECH = re.compile(r"/proc/|/dev/|/usr/|/etc/|/var/|\.py\b|\.sh\b|\.txt\b|\.conf\b|"
                  r"https?://|www\.|[A-Za-z]:\\|\\w+\.[a-z]{2,4}\b|"
                  r"CPU|MDR|SEBI|EPR|\d{2,}")

hits = []
for k, v in new.items():
    blob = v["sq"] + " " + v["en"]
    if TECH.search(blob):
        hits.append((k, v))
print("examples with a technical/path marker:", len(hits))
for k, v in hits[:14]:
    print("   %-14s %-56s | %s" % (k, v["sq"][:54], v["en"][:34]))

# word must appear as a standalone token bounded by non-letters
WORD = re.compile(r"[a-zA-Z\u00eb\u00cb\u00e7\u00c7]")
notstandalone = []
for k, v in new.items():
    toks = re.findall(r"[A-Za-z\u00eb\u00cb\u00e7\u00c7]+", v["sq"].lower())
    if k.lower() not in toks:
        notstandalone.append((k, v))
print()
print("examples where the deck word is NOT a standalone token:", len(notstandalone))
for k, v in notstandalone[:10]:
    print("   %-14s %s" % (k, v["sq"][:60]))
