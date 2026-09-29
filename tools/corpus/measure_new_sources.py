#!/usr/bin/env python3
"""What do the newly fetched human corpora add to the words still missing?

Streams each corpus once (HPLT alone is 1.8 GB, so nothing is held in memory)
and records which missing words appear at all, and in a teachable length.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "tools")
import select_examples as SE

D = Path("src_raw/opus")
NEW = ["bible-uedin", "ELRC-3052-wikipedia_health", "MaCoCu", "HPLT"]

deck = json.loads(Path("albcourse/data/words.json").read_text())["words"]
have = {w["sq"] for w in deck if w.get("ex")}
sel = json.loads(Path("albcourse/data/corpus_examples.json").read_text())
need = {w["sq"].lower() for w in deck if w["sq"] not in have and w["sq"] not in sel}
print("missing words:", len(need))
print()

for corpus in NEW:
    p = D / (corpus + ".txt")
    if not p.exists():
        print(corpus, "MISSING")
        continue
    found = set()
    inrange = set()
    n = 0
    with p.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "\t" not in line:
                continue
            parts = line.split("\t", 1)
            sq = parts[1].strip()
            if not sq:
                continue
            n += 1
            toks = set(SE.TOKEN_RE.findall(sq.lower()))
            hit = toks.intersection(need)
            if hit:
                found.update(hit)
                if 3 <= len(sq.split()) <= 9:
                    inrange.update(hit)
    print("%-32s %9d pairs  found %5d  in 3-9 words: %5d"
          % (corpus, n, len(found), len(inrange)))
    need = need.difference(found)
    print("%-32s still missing: %d" % ("", len(need)))

print()
print("STILL MISSING after all new human corpora:", len(need))
print()
print("sample of what is still missing:")
for w in sorted(need)[:20]:
    print("   ", w)
