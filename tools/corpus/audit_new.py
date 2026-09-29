#!/usr/bin/env python3
"""Audit the newly selected corpus examples against the previous run."""
import json, random, re, collections
from pathlib import Path

new = json.loads(Path("corpus_examples.json").read_text())
old = json.loads(Path("albcourse/data/corpus_examples.json").read_text())
deck = json.loads(Path("albcourse/data/words.json").read_text())["words"]

print("previous selection:", len(old))
print("new selection     :", len(new))
added = {k: v for k, v in new.items() if k not in old}
print("newly added       :", len(added))
print()

checks = {
    "no terminal punct":  lambda v: not re.search(r"[.!?]", v["sq"]),
    "identical sq/en":    lambda v: v["sq"].strip().lower() == v["en"].strip().lower(),
    "cyrillic":           lambda v: bool(re.search("[\u0400-\u04ff]", v["sq"] + v["en"])),
    "contains ..":        lambda v: ".." in v["sq"] or ".." in v["en"],
    "outside 3-9 words":  lambda v: not 3 <= len(v["sq"].split()) <= 9,
    "en too short":       lambda v: len(v["en"]) < 8,
    "quote or dash-gap":  lambda v: bool(re.search(r"[\u201c\u201d]|--| - ", v["sq"] + v["en"])),
}
for name, fn in checks.items():
    bad = [k for k, v in new.items() if fn(v)]
    print("%-20s %d" % (name, len(bad)))
    for k in bad[:2]:
        print("     %-14s %s | %s" % (k, new[k]["sq"][:46], new[k]["en"][:38]))

print()
print("=== 12 random NEW examples ===")
random.seed(11)
for k, v in random.sample(list(added.items()), min(12, len(added))):
    print("  %-16s %s" % (k, v["sq"]))
    print("  %-16s %s" % ("", v["en"][:70]))

print()
print("=== still missing (deck + new selection) ===")
have = {w["sq"] for w in deck if w.get("ex")}
missing = [w for w in deck if w["sq"] not in have and w["sq"] not in new]
print("count:", len(missing))
print("by POS:", collections.Counter(w["pos"][0] for w in missing if w["pos"]).most_common(6))
for w in sorted(missing, key=lambda x: x["rank"])[:10]:
    print("   L%-4d %-14s %-12s %s" % (w["level"], w["sq"], w["pos"][0] if w["pos"] else "-", w["en"][:42]))
