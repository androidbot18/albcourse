#!/usr/bin/env python3
"""Build data/words.json - a compact index of every card.

The level files carry full sense detail, etymology and category dumps, which is
right for a lesson view but too heavy to load 184 times over. This flattens the
deck into one small file the app can boot from, so a card is playable the
moment the page loads.

Kept deliberately minimal: only what the review card and the level map need.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LEVELS = DATA / "levels"


def dedup_labels(word):
    """POS labels for a card, deduped but order-preserving.

    Prefers the human-readable pos_labels and falls back to the short pos
    codes, so a card never ships a repeated label like
    ["conjunction", "conjunction"].
    """
    labels = word.get("pos_labels") or word.get("pos") or []
    seen, out = set(), []
    for label in labels:
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out


def first_example(word):
    for sense in word.get("sense_detail") or []:
        for ex in sense.get("examples") or []:
            if isinstance(ex, dict) and isinstance(ex.get("en"), str) and ex["en"].strip():
                return {"sq": ex.get("sq", ""), "en": ex["en"]}
    return None


def main():
    files = sorted(LEVELS.glob("level_*.json"))
    if not files:
        print("no level files found - run build_course.py first", file=sys.stderr)
        return 1

    words = []
    seen = set()
    for path in files:
        level = json.loads(path.read_text(encoding="utf-8"))
        n = level["level"]
        for w in level["words"]:
            if w["id"] in seen:
                print(f"duplicate id {w['id']} in level {n}", file=sys.stderr)
                return 1
            seen.add(w["id"])
            words.append(
                {
                    "id": w["id"],
                    "sq": w["sq"],
                    "en": w["en"],
                    "level": n,
                    "rank": w.get("rank"),
                    "family": w.get("family", w["id"]),
                    "is_root": bool(w.get("is_root")),
                    # Distinct labels only: pos_labels is aligned with
                    # glosses, so a homograph whose first two senses share a
                    # POS ("e" = conj + conj) would otherwise ship as
                    # ["conjunction", "conjunction"] and the card would
                    # render the label twice. Dedup, then cap at 2.
                    "pos": dedup_labels(w)[:2],
                    "etymology_class": w.get("etymology_class"),
                    "ex": first_example(w),
                }
            )

    out = DATA / "words.json"
    out.write_text(
        json.dumps({"version": 1, "count": len(words), "words": words}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"wrote {out.relative_to(ROOT)}: {len(words)} words from {len(files)} levels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
