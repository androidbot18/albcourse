#!/usr/bin/env python3
"""Re-run level assignment on the shipped deck, without the raw sources.

build_course.py needs the unpacked sources in data/raw/ (see
tools/fetch_sources.py). Level assignment does not: everything
assign_levels() reads -- rank, family, senses, components -- is already in
the shipped level files. So a change to the scheduler can be applied and
tested from the shipped data alone:

    python3 tools/relevel.py           # re-level data/, then rebuild words.json
    python3 tools/relevel.py --check   # exit 1 if data/ is not what the
                                       # current scheduler would produce

Both paths write through build_course.write_levels(), so a full rebuild and
a relevel produce the same files from the same cards. A full rebuild is still
the source of truth for everything else (glosses, examples, families).
"""
import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_course as bc  # noqa: E402


def shipped_cards():
    """Build-time-shaped cards and the level contents, read from data/levels."""
    files = sorted(glob.glob(os.path.join(bc.LEVELS_DIR, "level_*.json")),
                   key=lambda f: int(re.search(r"(\d+)\.json$", f).group(1)))
    cards, levels = [], []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            lvl = json.load(fh)
        levels.append([w["sq"] for w in lvl["words"]])
        for w in lvl["words"]:
            c = dict(w)
            c["word"] = w["sq"]
            c["senses"] = w["sense_detail"]
            cards.append(c)
    return cards, levels


def snapshot():
    """Every file relevel writes, as {path: bytes}."""
    paths = glob.glob(os.path.join(bc.LEVELS_DIR, "level_*.json"))
    paths += [os.path.join(bc.OUT, n)
              for n in ("course.json", "index.json", "report.json", "words.json")]
    out = {}
    for p in paths:
        with open(p, "rb") as fh:
            out[p] = fh.read()
    return out


def main(argv):
    check = "--check" in argv
    before = snapshot() if check else None

    cards, _ = shipped_cards()
    families = {}
    for c in cards:
        families.setdefault(c["family"], []).append(c["word"])
    by_word = {c["word"]: c for c in cards}
    corpus_examples = {c["word"]: c["corpus_example"] for c in cards
                       if c.get("corpus_example") is not None}

    levels = bc.schedule_course(cards, families,
                                components=bc.by_word_components(cards),
                                opening=bc.opening_levels.LEVELS)
    level_objs = bc.write_levels(levels, by_word, corpus_examples)

    report_path = os.path.join(bc.OUT, "report.json")
    with open(report_path, encoding="utf-8") as fh:
        report = json.load(fh)
    report["levels"] = len(level_objs)
    report["main_levels"] = sum(1 for l in level_objs if not l.get("extended"))
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    subprocess.run([sys.executable, os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "build_words_index.py")], check=True)
    print("relevelled: %d cards in %d levels" % (len(cards), len(level_objs)))

    if check:
        after = snapshot()
        changed = sorted(os.path.relpath(p, bc.ROOT)
                         for p in set(before) | set(after)
                         if before.get(p) != after.get(p))
        # Put the shipped files back: --check reports, it never rewrites.
        for p in set(after) - set(before):
            os.remove(p)
        for p, data in before.items():
            with open(p, "wb") as fh:
                fh.write(data)
        if changed:
            print("data/ is stale against the scheduler; %d files differ, "
                  "e.g. %s" % (len(changed), ", ".join(changed[:5])))
            return 1
        print("data/ matches the scheduler")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
