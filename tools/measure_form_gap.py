#!/usr/bin/env python3
"""How much high-frequency vocabulary is the deck losing to sense_is_content?

'sense_is_content' drops any sense tagged form-of/alt-of, on the reasoning that
an inflected form is already covered by its lemma's inflection table. That is
right for a dictionary and wrong for a course: in Albanian the learner meets
'është' and 'janë' as words, and 'është' is rank 6 in the frequency list. It is
absent from the deck.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
import build_course as B

freq = B.load_freq("data/raw/sq_50k.txt")
deck = {w["sq"] for w in json.loads(Path("data/words.json").read_text())["words"]}

# Every sq entry that passes the shape + frequency gates but yields no content
# sense. Those are the words the deck is silently losing.
lost = []
tags_seen = Counter()
pos_seen = Counter()
with open("data/raw/kaikki_albanian.jsonl", encoding="utf-8") as fh:
    for line in fh:
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("lang_code") != "sq":
            continue
        if d.get("pos") not in B.CORE_POS:
            continue
        w = (d.get("word") or "").strip()
        if not w or not B.ALPHABET_RE.match(w):
            continue
        f = freq.get(w)
        if not f:
            continue
        if w in deck:
            continue
        if B.entry_senses(d):
            continue
        lost.append((f[0], w, d.get("pos")))
        pos_seen[d.get("pos")] += 1
        for s in d.get("senses") or []:
            for t in (s.get("tags") or []):
                tags_seen[t] += 1

print("high-frequency entries dropped by sense_is_content:", len(lost))
print("by pos:", pos_seen.most_common(8))
print("top tags:", tags_seen.most_common(6))
print()
print("most frequent dropped words:")
for rank, w, pos in sorted(lost)[:30]:
    print("   rank %-6d %-14s %-8s" % (rank, w, pos))
inside = [r for r, w, _ in lost if r <= 500]
print()
print("of these, %d are in the frequency list's top 500" % len(inside))
