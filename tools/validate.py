#!/usr/bin/env python3
"""Integrity checks on the generated course data. Run after build_course.py."""

import json
import os
import teaching_order
import re
import sys
import unicodedata
from collections import Counter, defaultdict

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


# Session shape, kept in step with assign_levels() in build_course.py.
PER_LEVEL = 9
MAX_FAMILIES = 6


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
    fam_parts = defaultdict(list)   # family -> [(part, parts, level)]
    last_part = {}   # family -> (last part seen, the level it was on)
    for i, fname in enumerate(files, 1):
        lvl = json.load(open(os.path.join(LEVELS_DIR, fname), encoding="utf-8"))
        nw, nfam = lvl["word_count"], len(lvl["families"])
        # These mirror assign_levels()'s per_level / max_families. They were
        # 9 and 3 when the course had ~3000 mostly-singleton families, which
        # forced 1031 levels. The packer now groups up to 6 roots per level to
        # reach the 600-level target, so the guard has to move with it --
        # otherwise the validator just reports the new, intended shape as a bug.
        if nw > PER_LEVEL:
            struct.append("%s: %d words (>%d, level must be session-sized)"
                          % (fname, nw, PER_LEVEL))
        if nfam > MAX_FAMILIES:
            struct.append("%s: %d families (>%d roots in one level)"
                          % (fname, nfam, MAX_FAMILIES))
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
            elif parts > 1 and part > 1 and last_part.get(f, (0, None))[1] != i - 1:
                # A continuation must sit IMMEDIATELY after the PREVIOUS
                # part, not merely somewhere after part 1. Comparing
                # against part 1 was wrong: a 7-part family occupying
                # levels 5..11 is perfectly consecutive and was reported
                # as a violation.
                prev_part, prev_lvl = last_part.get(f, (0, None))
                struct.append("%s: continuation part %d/%d of %r follows part %d on level %s, not the level before it"
                              % (fname, part, parts, f, prev_part, prev_lvl))
            if parts > 1:
                last_part[f] = (part, i)
        for w in lvl["words"]:
            fam_parts.setdefault(w["family"], set()).add(
                (lvl.get("part", 1), lvl.get("parts", 1), i))

    # A split family must be consecutive 1/n, 2/n, ... AND every one of its
    # levels must agree on the total n. Checking each level on its own is not
    # enough: a level claiming part 2 of 10 while its sibling claims part 1 of
    # 7 is internally valid and slips straight through.
    for f, seen in fam_parts.items():
        totals = {tot for _, tot, _ in seen}
        if len(totals) > 1:
            struct.append("family %r disagrees on its part count: %s"
                          % (f, sorted(totals)))
        lvls = sorted(x[2] for x in seen)
        if len(lvls) <= 1:
            continue
        if lvls != list(range(lvls[0], lvls[0] + len(lvls))):
            struct.append("family %r spans non-consecutive levels %s" % (f, lvls))
        ordered = [x[0] for x in sorted(seen, key=lambda x: x[2])]
        if ordered != list(range(1, len(ordered) + 1)):
            struct.append("family %r has parts %s, expected 1..%d"
                          % (f, ordered, len(ordered)))

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
        # Order within a level is teaching order: tense/register tier
        # first, corpus frequency second. Sorting by rank alone is what
        # the build used to do, and it put a verb's rare perfect forms
        # ahead of its present tense, so the check has to follow the new
        # rule or it would demand the behaviour we just removed.
        keys = [teaching_order.level_key(
                    {"senses": [{"gloss": w["en"]}], "rank": w["rank"]},
                    is_root=(w["id"] == lvl["root"])) for w in lvl["words"]]
        if keys != sorted(keys):
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
    check(not unsorted_levels,
          "levels not in teaching order: %s" % unsorted_levels[:10])

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
