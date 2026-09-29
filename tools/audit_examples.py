#!/usr/bin/env python3
"""Audit how much real example material the upstream source actually holds.

The course needs an Albanian example sentence for (nearly) every card. The
question this answers: is the gap fixable by better selection from the source,
or does the source simply not contain the material?
"""
import collections
import json
import os
import sys

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "kaikki_albanian.jsonl")


def main() -> int:
    if not os.path.exists(RAW):
        print(f"missing raw source: {RAW}")
        print("run tools/fetch_sources.py first")
        return 1

    entry_senses = 0
    senses_with_ex = 0
    ex_total = 0
    words_with_ex = collections.Counter()
    both_sides = 0

    with open(RAW, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            word = d.get("word")
            if not word:
                continue
            got = 0
            for sense in d.get("senses") or []:
                entry_senses += 1
                exs = sense.get("examples") or []
                if exs:
                    senses_with_ex += 1
                for ex in exs:
                    text = (ex.get("text") or "").strip()
                    if not text:
                        continue
                    got += 1
                    ex_total += 1
                    if (ex.get("english") or "").strip():
                        both_sides += 1
            if got:
                words_with_ex[word] += got

    print(f"senses total            {entry_senses}")
    print(f"senses with >=1 example {senses_with_ex}")
    print(f"examples total          {ex_total}")
    print(f"examples w/ english     {both_sides}")
    print(f"distinct words w/ ex    {len(words_with_ex)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
