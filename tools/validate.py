#!/usr/bin/env python3
"""Integrity checks on the generated course data. Run after build_course.py."""

import json
import os
import re
import sys
import unicodedata
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data")
LEVELS_DIR = os.path.join(OUT, "levels")

SQ_LETTER = re.compile("^[A-Za-zëçËÇ]+$")
REQUIRED_WORD_KEYS = {
    "id", "sq", "en", "glosses", "pos", "pos_labels", "sense_detail",
    "rank", "count", "family", "is_root", "etymology", "etymology_class",
    "source_lang", "parents", "derived", "related", "forms",
}
FORBIDDEN = {"_score", "score", "sense", "raw"}

fail = []
warn = []


def check(cond, msg):
    if not cond:
        fail.append(msg)
    return cond


def main():
    course_p = os.path.join(OUT, "course.json")
    index_p = os.path.join(OUT, "index.json")
    if not (os.path.exists(course_p) and os.path.exists(index_p)):
        print("FAIL: data/course.json or data/index.json missing - run build_course.py")
        return 2

    course = json.load(open(course_p, encoding="utf-8"))
    index = json.load(open(index_p, encoding="utf-8"))

    # Sort by the numeric suffix, not lexicographically: filenames are
    # zero-padded to a fixed width, so a plain sorted() would put
    # "level_100.json" before "level_11.json" and every level check would
    # be off by a block.
    files = sorted(
        (f for f in os.listdir(LEVELS_DIR) if f.endswith(".json")),
        key=lambda f: int(re.search(r"(\d+)", f).group(1)),
    )
    print("level files on disk: %d" % len(files))
    check(len(files) == course["level_count"],
          "level_count=%d but %d level files exist" % (course["level_count"], len(files)))
    check(len(files) == len(index),
          "index.json has %d entries, %d files on disk" % (len(index), len(files)))

    # --- level structure: a level is a session of whole word families -----
    # These guard the invariants assign_levels() is supposed to guarantee,
    # so a future change to the packer cannot quietly re-scatter families.
    struct = []
    fam_levels = {}
    cont_level = {}
    for i, fname in enumerate(files, 1):
        lvl = json.load(open(os.path.join(LEVELS_DIR, fname), encoding="utf-8"))
        nw, nfam = lvl["word_count"], len(lvl["families"])
        if nw > 9:
            struct.append("%s: %d words (>9, level must be session-sized)" % (fname, nw))
        if nfam > 3:
            struct.append("%s: %d families (>3 roots in one level)" % (fname, nfam))
        if not lvl.get("title"):
            struct.append("%s: missing title" % fname)
        # every word in a level must belong to a family listed for that level
        stray = {w["family"] for w in lvl["words"]} - set(lvl["families"])
        if stray:
            struct.append("%s: words reference unlisted families %s" % (fname, sorted(stray)))
        # a single-family level must be exactly that family, and if that
        # family is split the part metadata must be truthful and sequential
        if nfam == 1:
            f = lvl["families"][0]
            if lvl.get("root") != f:
                struct.append("%s: root=%r but families=[%r]" % (fname, lvl.get("root"), f))
            part, parts = lvl.get("part"), lvl.get("parts")
            if not isinstance(parts, int) or parts < 1 or not isinstance(part, int) or not 1 <= part <= parts:
                struct.append("%s: bad part/part= %r/%r" % (fname, part, parts))
            elif parts > 1 and part > 1 and cont_level.get(f) != i - 1:
                struct.append("%s: continuation part %d/%d of %r is not the level right after its first part"
                              % (fname, part, parts, f))
            if parts > 1 and part == 1:
                cont_level[f] = i
        for w in lvl["words"]:
            fam_levels.setdefault(w["family"], set()).add(i)

    # a family split across levels must do so as consecutive 1/n,2/n levels
    for f, lv in fam_levels.items():
        if len(lv) <= 1:
            continue
        if sorted(lv) != list(range(min(lv), max(lv) + 1)):
            struct.append("family %r spans non-consecutive levels %s" % (f, sorted(lv)))

    check(not struct,
          "level structure violations:\n    " + "\n    ".join(struct[:20]))

    seen_ids = Counter()
    total = 0
    pos_counter = Counter()
    dia_words = []
    bad_letters = []
    empty_gloss = []
    leaked = []
    missing_keys = []
    unsorted_levels = []
    n_ex = 0
    bad_examples = []

    for i, fname in enumerate(files, 1):
        lvl = json.load(open(os.path.join(LEVELS_DIR, fname), encoding="utf-8"))
        check(lvl["level"] == i, "%s: level field is %s, expected %d" % (fname, lvl["level"], i))
        check(lvl["word_count"] == len(lvl["words"]),
              "%s: word_count=%d but %d words present" % (fname, lvl["word_count"], len(lvl["words"])))
        if not lvl["words"]:
            fail.append("%s: is empty" % fname)
            continue
        ranks = [w["rank"] for w in lvl["words"]]
        if ranks != sorted(ranks):
            unsorted_levels.append(fname)
        for w in lvl["words"]:
            total += 1
            seen_ids[w["id"]] += 1
            if not w.get("sq") or not SQ_LETTER.match(w["sq"]):
                bad_letters.append((fname, w.get("id")))
            if not w.get("glosses"):
                empty_gloss.append((fname, w.get("id")))
            for k in REQUIRED_WORD_KEYS:
                if k not in w:
                    missing_keys.append((fname, w.get("id"), k))
            for s in w.get("sense_detail", []):
                for k in s:
                    if k in FORBIDDEN:
                        leaked.append((fname, w.get("id"), k))
                # Examples must be structured objects, never str()-ed dicts.
                # That bug shipped once; keep a guard so it cannot come back.
                for ex in s.get("examples", []):
                    n_ex += 1
                    if not isinstance(ex, dict):
                        bad_examples.append((fname, w.get("id"), "not an object: %r" % (ex,)[:80]))
                        continue
                    for k in ("sq", "en", "offsets"):
                        if k not in ex:
                            bad_examples.append((fname, w.get("id"), "missing %r" % k))
            for p in w.get("pos", []):
                pos_counter[p] += 1
            if w.get("id") != w.get("sq"):
                bad_letters.append((fname, "id!=sq %r/%r" % (w.get("id"), w.get("sq"))))
            if w["sq"] != unicodedata.normalize("NFC", w["sq"]):
                warn.append("%s: %r is not NFC-normalised" % (fname, w["sq"]))
            if any(c in w["sq"] for c in "ëçËÇ"):
                dia_words.append(w["sq"])

    dups = {k: v for k, v in seen_ids.items() if v > 1}
    check(not dups, "duplicate word ids: %s" % list(dups.items())[:10])
    check(not bad_examples,
          "malformed examples (str()-ed dicts?): %s" % bad_examples[:5])
    check(total == course["word_count"],
          "course.word_count=%d but %d cards across levels" % (course["word_count"], total))
    check(not bad_letters, "headwords with invalid letters or id!=sq: %s" % bad_letters[:10])
    check(not empty_gloss, "cards with no gloss: %s" % empty_gloss[:10])
    check(not leaked, "build-time fields leaked into output: %s" % leaked[:10])
    check(not missing_keys, "cards missing required keys: %s" % missing_keys[:10])
    check(not unsorted_levels, "levels not sorted by rank: %s" % unsorted_levels[:10])

    # --- flat index (data/words.json) -------------------------------
    # words.json is what the live site actually boots from, so it needs the
    # same guarantees as the level files even though it is much smaller.
    words_p = os.path.join(OUT, "words.json")
    if os.path.exists(words_p):
        flat = json.load(open(words_p, encoding="utf-8"))
        fw = flat.get("words", [])
        check(flat.get("count") == len(fw),
              "words.json count=%s but %d words listed" % (flat.get("count"), len(fw)))
        check(len(fw) == total,
              "words.json has %d cards, level files have %d" % (len(fw), total))
        check({w["id"] for w in fw} == set(seen_ids),
              "words.json id set does not match the level files")
        dup_pos = [w["id"] for w in fw if len(w.get("pos") or []) != len(set(w.get("pos") or []))]
        check(not dup_pos,
              "%d cards repeat a POS label (e.g. %s)" % (len(dup_pos), dup_pos[:5]))
        # pos_labels is aligned with glosses in the level files and may
        # legitimately repeat; the flattened index must not.
        print()
        print("flat index:            %d cards, %d with two POS labels"
              % (len(fw), sum(1 for w in fw if len(w.get("pos") or []) == 2)))
    else:
        warn.append("data/words.json missing - run build_words_index.py")

    ndia = len(set(dia_words))
    if ndia < 200:
        fail.append("only %d distinct diaeresis/cedilla words survived" % ndia)

    fams = Counter()
    for fname in files:
        lvl = json.load(open(os.path.join(LEVELS_DIR, fname), encoding="utf-8"))
        for w in lvl["words"]:
            fams[w["family"]] += 1
    orphan = [r for r in fams if r not in seen_ids]
    if orphan:
        warn.append("%d family roots not in deck (e.g. %s)" % (len(orphan), orphan[:5]))

    print()
    print("example pairs:        %d" % n_ex)
    print("cards:                 %d" % total)
    print("levels:                %d" % len(files))
    print("distinct ids:          %d" % len(seen_ids))
    print("words with e-dia/ç:    %d" % ndia)
    print("families:              %d" % len(fams))
    print("multi-member families: %d" % sum(1 for v in fams.values() if v > 1))
    print("POS mix:               %s" % dict(pos_counter.most_common()))

    if warn:
        print()
        print("WARNINGS (%d):" % len(warn))
        for w in warn[:15]:
            print("  ~ %s" % w)

    if fail:
        print()
        print("FAILURES (%d):" % len(fail))
        for f in fail:
            print("  x %s" % f)
        return 1

    print()
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
