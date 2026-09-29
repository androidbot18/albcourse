#!/usr/bin/env python3
"""Measure how much of the Albanian course deck the OPUS corpora can cover."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "src_raw" / "opus"
WORDS_JSON = ROOT / "albcourse" / "data" / "words.json"

HUMAN = ["Tatoeba", "EUbookshop", "TildeMODEL", "GlobalVoices", "TED2020",
         "QED", "GNOME", "SETIMES"]
OTHER = ["WikiMatrix", "wikimedia", "Tanzil"]

TOKEN_RE = re.compile(r"[a-zA-Z\u00eb\u00cb\u00e7\u00c7]+")


def load_pairs(name):
    path = CORPUS_DIR / (name + ".txt")
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "\t" not in line:
            continue
        en, sq = line.split("\t", 1)
        if en.strip() and sq.strip():
            rows.append((en.strip(), sq.strip()))
    return rows


def tokens(text):
    return set(TOKEN_RE.findall(text.lower()))


def main():
    deck = {w["sq"] for w in json.loads(WORDS_JSON.read_text())["words"]}
    print("deck words:", len(deck))

    cumulative = set()
    print()
    print("%-14s %8s %9s %9s" % ("corpus", "pairs", "new", "cumulative"))
    for name in HUMAN + OTHER:
        rows = load_pairs(name)
        hit = set()
        for _en, sq in rows:
            hit.update(tokens(sq).intersection(deck))
        new = hit.difference(cumulative)
        cumulative.update(hit)
        print("%-14s %8d %9d %9d" % (name, len(rows), len(new), len(cumulative)))

    total = len(cumulative)
    print()
    print("any corpus   : %d / %d = %.1f%%" % (total, len(deck), 100.0 * total / len(deck)))

    human_only = set()
    for name in HUMAN:
        for _en, sq in load_pairs(name):
            human_only.update(tokens(sq).intersection(deck))
    print("human only   : %d / %d = %.1f%%" % (len(human_only), len(deck), 100.0 * len(human_only) / len(deck)))
    print("human misses : %d" % (len(deck) - len(human_only)))

    short = 0
    for name in HUMAN:
        for _en, sq in load_pairs(name):
            if 2 <= len(sq.split()) <= 7:
                short += 1
    print("human sentences of 2-7 words:", short)


if __name__ == "__main__":
    main()
