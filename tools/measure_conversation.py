#!/usr/bin/env python3
"""Measure the course against the conversational goals in CONVERSATION_PLAN.md.

Prints the figures the plan's gates are stated in, from the shipped data:
where the checklist words are taught, how much of the main course is
inflected forms, how many phrases there are, and how readable the examples
are. Nothing here is estimated.

    python3 tools/measure_conversation.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import conversation_checklist as checklist  # noqa: E402
import conversation_core as cc  # noqa: E402

NEW_PER_DAY = 20          # the app's daily cap on new cards
MONTH = 30 * NEW_PER_DAY  # cards a learner reaches in the first month


def taught_at(core, kk):
    """{token: position} of the first core item that teaches each token."""
    first = {}
    n = 0
    for u in core["units"]:
        for it in u["items"]:
            n += 1
            for t in cc.known_forms(it, kk):
                first.setdefault(t, n)
    return first


def checklist_report(core, kk):
    first = taught_at(core, kk)
    rows = []
    for w in dict.fromkeys(checklist.WORDS):
        toks = [t.lower() for t in re.split(r"['’]", w) if t]
        pos = max((first.get(t, 10 ** 9) for t in toks), default=10 ** 9)
        rows.append((w, None if pos == 10 ** 9 else pos))
    return rows


def main():
    core = cc.load()
    kk = cc.kaikki_forms()
    if not kk:
        print("no data/raw sources - run tools/fetch_sources.py", file=sys.stderr)
        return 2
    with open(os.path.join(ROOT, "data", "words.json"), encoding="utf-8") as fh:
        words = json.load(fh)["words"]
    main_cards = [w for w in words if not w.get("extended")]
    core_ids = cc.words_of(core)
    core_cards = [w for w in words if w["sq"] in core_ids]
    items = [it for u in core["units"] for it in u["items"]]
    word_items = [it for it in items if it["pos"] != "phrase"]

    print("CONVERSATION CORE")
    print("  units / levels                     %d / %d"
          % (len(core["units"]), len(cc.lessons(core))))
    print("  words / phrases                    %d / %d"
          % (len(word_items), len(items) - len(word_items)))
    print("  days to finish at %d new a day      %d"
          % (NEW_PER_DAY, -(-len(items) // NEW_PER_DAY)))

    rows = checklist_report(core, kk)
    missing = [w for w, p in rows if p is None and w not in checklist.SKIPPED]
    skipped = [w for w, p in rows if p is None and w in checklist.SKIPPED]
    late = [(w, p) for w, p in rows if p is not None and p > MONTH]
    print("\nCHECKLIST (%d everyday words)" % len(rows))
    print("  taught in the core                 %d"
          % sum(1 for _, p in rows if p is not None))
    print("  ...within the first month (%d items) %d"
          % (MONTH, sum(1 for _, p in rows if p is not None and p <= MONTH)))
    print("  after the first month              %d  %s"
          % (len(late), " ".join("%s(%d)" % x for x in late[:12])))
    print("  deliberately not taught            %d  %s"
          % (len(skipped), " ".join(skipped)))
    print("  missing                            %d  %s"
          % (len(missing), " ".join(missing)))

    # A form card's gloss ends "(from <word>, <its meaning>)".
    forms = [w["sq"] for w in main_cards
             if re.search(r"\(from [^()]+, [^()]+\)$", w["en"])]
    print("\nONE CARD PER WORD")
    print("  main-course cards                  %d" % len(main_cards))
    print("  ...that are an inflected form      %d  %s"
          % (len(forms), " ".join(forms)))
    print("  core cards showing key forms       %d of %d"
          % (sum(1 for w in core_cards if w.get("forms")), len(word_items)))

    ex = [it["ex"]["sq"] for it in word_items if it["ex"]]
    lens = sorted(len(cc.tokens(s)) for s in ex)
    problems = cc.check(core, kk)
    print("\nREADABLE SENTENCES")
    print("  core words with an example         %d of %d" % (len(ex), len(word_items)))
    print("  example length, median / longest   %d / %d words"
          % (lens[len(lens) // 2], lens[-1]))
    print("  sentences using an untaught word   %d" % len(problems))
    print("  unit dialogues                     %d of %d units"
          % (sum(1 for u in core["units"] if u["dialogue"]), len(core["units"])))
    over = [it["sq"] for it in word_items if len(it["en"]) > 30]
    print("  headline glosses over 30 chars     %d" % len(over))
    return 0


if __name__ == "__main__":
    sys.exit(main())
