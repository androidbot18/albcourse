"""Measure the session shape the level packer actually produced.

Answers the questions the sequencing review raised, from the shipped data
rather than from a plan: how many levels, how big, how root-homogeneous, and
where the common words land.
"""
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS = os.path.join(ROOT, "data", "levels")


def main():
    files = sorted(
        (f for f in os.listdir(LEVELS) if f.endswith(".json")),
        key=lambda f: int(re.search(r"(\d+)", f).group(1)),
    )
    sizes = []
    homog = 0
    n = 0
    total_words = 0
    first_levels = []
    word_level = {}

    for i, fname in enumerate(files, 1):
        lvl = json.load(open(os.path.join(LEVELS, fname), encoding="utf-8"))
        n += 1
        sizes.append(lvl["word_count"])
        total_words += lvl["word_count"]
        if len(lvl["families"]) == 1:
            homog += 1
        for w in lvl["words"]:
            word_level.setdefault(w["sq"], i)
        if i <= 10:
            first_levels.append((i, lvl["title"],
                                 [w["sq"] for w in lvl["words"]]))

    print("levels: %d" % n)
    print("cards: %d" % total_words)
    print("mean words/level: %.1f" % (sum(sizes) / float(len(sizes))))
    print("min %d  max %d" % (min(sizes), max(sizes)))
    print("levels under 5 words: %d" % sum(1 for s in sizes if s < 5))
    print("levels with 1 family (root-homogeneous): %d (%.1f%%)"
          % (homog, 100.0 * homog / n))

    print("\n-- first 10 levels --")
    for i, title, words in first_levels:
        print("L%-3d %-38s %s" % (i, title[:38], " ".join(words)))

    c = Counter()
    for fname in files[:10]:
        lvl = json.load(open(os.path.join(LEVELS, fname), encoding="utf-8"))
        for w in lvl["words"]:
            for p in (w.get("pos") or ["?"]):
                c[p] += 1
    tot = sum(c.values()) or 1
    print("\n-- part-of-speech mix, levels 1-10 --")
    for p, k in c.most_common(8):
        print("  %-8s %4d  %5.1f%%" % (p, k, 100.0 * k / tot))
    print("  noun share: %.1f%%" % (100.0 * c.get("noun", 0) / tot))

    # words.json is the flat index the browser loads: {version, count, words}.
    # Rank lives there, not in course.json or index.json.
    words_p = os.path.join(ROOT, "data", "words.json")
    flat = json.load(open(words_p, encoding="utf-8"))["words"]
    top = sorted(flat, key=lambda w: w.get("rank", 10 ** 9))[:100]
    spread = Counter(word_level.get(w["sq"], -1) for w in top)
    print("\n-- top 100 words by rank --")
    print("distinct levels they land in: %d" % len(spread))
    print("deepest level any of them reaches: %d" % max(spread))
    in50 = sum(1 for lv in spread if 0 < lv <= 50)
    print("of the first 50 levels, %d contain no top-100 word" % (50 - in50))
    tail = sum(1 for lv in spread if lv > 300)
    print("top-100 words landing past level 300: %d" % tail)
    return 0


if __name__ == "__main__":
    sys.exit(main())
