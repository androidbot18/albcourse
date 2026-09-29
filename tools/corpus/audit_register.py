#!/usr/bin/env python3
"""Is HPLT's wiki prose safe to teach from?

Structural gates all pass, but register is a separate axis: 'uri' (the noun
'hunger') was illustrated with 'A ka ftohte ose uri?' / 'Is it cold or hungry?',
where the word is being used as the verb 'to go mad'. This counts how often the
chosen HPLT sentences carry wiki/technical/encyclopedic markers, and compares
against the curated corpora, so the decision to keep HPLT is measured rather
than assumed.
"""
import json, re, collections
from pathlib import Path

sel = json.loads(Path("corpus_examples.json").read_text())
by = collections.Counter(v["corpus"] for v in sel.values())
print("selection by corpus:")
for k, v in by.most_common():
    print("   %-16s %5d" % (k, v))

WIKI = re.compile(
    r"\bwiki|\bfaq|\bhttp|wikipedia|\bsoft|\bserver|\bnder\b|\bformat|\bdefault\b|"
    r"\bstandard\b|\bversion\b|\bkonfigur|\bsistem\b|\bkompil|\bdatabase\b|"
    r"\bprogram\b|\bfunksion\b|\bmetod\b|\bkërkohet|\bredirect\b|\bfaq\b",
    re.I)

print()
print("wiki/technical register markers, by corpus:")
for corpus in by:
    rows = [v for v in sel.values() if v["corpus"] == corpus]
    hit = [v for v in rows if WIKI.search(v["sq"] + " " + v["en"])]
    pct = 100.0 * len(hit) / max(1, len(rows))
    print("   %-16s %4d / %4d  = %5.1f%%" % (corpus, len(hit), len(rows), pct))

# how much coverage do we lose if HPLT is dropped entirely?
deck = json.loads(Path("albcourse/data/words.json").read_text())["words"]
wik = 0
for w in deck:
    for s in w.get("sense_detail") or []:
        if any(e.get("en") for e in (s.get("examples") or [])):
            wik += 1
            break
nohplt = sum(1 for v in sel.values() if v["corpus"] != "HPLT")
print()
print("wiktionary examples        :", wik)
print("corpus examples, no HPLT   :", nohplt)
print("coverage without HPLT      : %.1f%%" % (100.0 * (wik + nohplt) / len(deck)))
print("coverage with HPLT         : %.1f%%" % (100.0 * (wik + len(sel)) / len(deck)))
