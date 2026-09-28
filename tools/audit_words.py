#!/usr/bin/env python3
"""Audit data/words.json for data-quality defects.

Focus: duplicate POS tags. Every card in the shipped data carries a `pos`
list, and homograph merging appends one entry per sense -- so a word with
two noun senses ends up as ["noun", "noun"], which is meaningless metadata
for the app and for any downstream exporter.
"""
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS = os.path.join(ROOT, "data", "words.json")


def main() -> int:
    with open(WORDS, encoding="utf-8") as fh:
        data = json.load(fh)
    words = data["words"]

    dup = [w for w in words if len(w["pos"]) != len(set(w["pos"]))]
    print(f"cards: {len(words)}")
    print(f"cards with duplicate POS tags: {len(dup)} "
          f"({100.0 * len(dup) / len(words):.1f}%)")
    print(f"cards with >1 entry in pos:   {sum(1 for w in words if len(w['pos']) > 1)}")
    print(f"cards with >1 DISTINCT pos:   {sum(1 for w in words if len(set(w['pos'])) > 1)}")

    if dup:
        print("\ntop duplicated-pos shapes:")
        for shape, n in collections.Counter(
            tuple(sorted(set(w["pos"]))) for w in dup
        ).most_common(8):
            print(f"  {n:5d}  {shape}")

    # What the dedup would look like, and whether it loses ordering info.
    if dup:
        print("\nsample raw pos -> deduped pos:")
        for w in dup[:8]:
            seen, ordered = set(), []
            for p in w["pos"]:
                if p not in seen:
                    seen.add(p)
                    ordered.append(p)
            print(f"  {w.get('id', w.get('sq', '?')):<12} {w['pos']}  ->  {ordered}")
    else:
        print("\nNo duplicate POS tags. Every card carries distinct labels.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
