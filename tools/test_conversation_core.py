#!/usr/bin/env python3
"""The Conversation Core keeps the gates in CONVERSATION_PLAN.md.

  * every checklist word is taught in the core;
  * no core card is an inflected form of another card;
  * at least 150 phrases;
  * every core word has an example of 8 words or fewer in which every
    other word was taught on the same level or earlier;
  * every headline gloss is 30 characters or fewer;
  * every unit closes with a dialogue made of taught words.

Each rule has a negative control, so a check that cannot fail is caught.
"""
import copy
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import conversation_checklist as checklist  # noqa: E402
import conversation_core as cc  # noqa: E402
import measure_conversation as mc  # noqa: E402

failures = []


def check(name, ok):
    print("  %s %s" % ("ok  " if ok else "FAIL", name))
    if not ok:
        failures.append(name)


core = cc.load()
kk = cc.kaikki_forms()
if not kk:
    print("skip: data/raw not present - run tools/fetch_sources.py")
    sys.exit(0)

items = [it for u in core["units"] for it in u["items"]]
words = [it for it in items if it["pos"] != "phrase"]
phrases = [it for it in items if it["pos"] == "phrase"]

print("== the content ==")
check("about 1,000 words (%d)" % len(words), 950 <= len(words) <= 1100)
check("at least 150 phrases (%d)" % len(phrases), len(phrases) >= 150)
check("a level holds at most %d items" % cc.PER_LEVEL,
      all(len(l["items"]) <= cc.PER_LEVEL for l in cc.lessons(core)))
sizes = [len(u["items"]) for u in core["units"]]
check("a unit is a few lessons, not a wall (%d-%d items)"
      % (min(sizes), max(sizes)), min(sizes) >= 12 and max(sizes) <= 40)
check("every unit says what the learner can now do",
      all(u["can_do"] for u in core["units"]))
check("every headline gloss is 30 characters or fewer",
      all(len(it["en"]) <= 30 for it in words))
check("every word has an example with a translation",
      all(it["ex"] and it["ex"]["en"] for it in words))

print("\n== readable sentences ==")
problems = cc.check(core, kk)
check("no example or dialogue uses an untaught word (%s)" % problems[:2],
      not problems)


def mutated(fn):
    c = copy.deepcopy(core)
    fn(c)
    return cc.check(c, kk)


def first_word(c):
    return next(it for it in c["units"][0]["items"] if it["pos"] != "phrase")


def untaught(c):
    first_word(c)["ex"]["sq"] += " Autobusi niset."


def too_long(c):
    it = next(x for x in c["units"][5]["items"] if x["pos"] != "phrase")
    it["ex"]["sq"] = " ".join([it["sq"]] * 9)


def unused(c):
    first_word(c)["ex"]["sq"] = "Po."


def no_example(c):
    first_word(c)["ex"] = None


def bad_dialogue(c):
    c["units"][0]["dialogue"].append({"sq": "Ku është stacioni?", "en": "x"})


def no_dialogue(c):
    c["units"][3]["dialogue"] = []


for name, fn, needle in (
        ("a later word in an early example", untaught, "untaught"),
        ("an example over 8 words", too_long, "max 8"),
        ("an example that does not use its word", unused, "does not use"),
        ("a word with no example", no_example, "no example"),
        ("a dialogue with an untaught word", bad_dialogue, "dialogue uses"),
        ("a unit with no dialogue", no_dialogue, "no dialogue")):
    got = mutated(fn)
    check("control: %s is caught" % name, any(needle in p for p in got))

# The order inside a level matters: a word may lean on the one before it.
c2 = copy.deepcopy(core)
u = c2["units"][1]
u["items"].reverse()
check("control: reversing a unit breaks its sentences", bool(cc.check(c2, kk)))

print("\n== the checklist ==")
rows = mc.checklist_report(core, kk)
missing = sorted(w for w, p in rows if p is None and w not in checklist.SKIPPED)
check("every checklist word is taught in the core (missing: %s)" % missing,
      not missing)
check("every skip names a word on the list",
      set(checklist.SKIPPED) <= set(checklist.WORDS))
c3 = copy.deepcopy(core)
for u in c3["units"]:
    u["items"] = [it for it in u["items"] if it["sq"] != "restorant"]
check("control: a dropped checklist word is noticed",
      any(w == "restorant" and p is None for w, p in mc.checklist_report(c3, kk)))

print("\n== shipped data ==")
files = sorted(glob.glob(os.path.join(ROOT, "data", "levels", "level_*.json")),
               key=lambda f: int(re.search(r"(\d+)\.json$", f).group(1)))
shipped = [json.load(open(f, encoding="utf-8")) for f in files]
flat = json.load(open(os.path.join(ROOT, "data", "words.json"),
                      encoding="utf-8"))["words"]
by_id = {w["id"]: w for w in flat}
lessons = cc.lessons(core)
if not shipped:
    print("  skip data/levels not built")
else:
    core_levels = [L for L in shipped if L.get("unit")]
    check("the core is levels 1-%d" % len(lessons),
          [L["level"] for L in core_levels] == list(range(1, len(lessons) + 1)))
    check("each core level carries its unit and situation",
          all(L["unit"] == les["unit"] and L["situation"] == les["situation"]
              for L, les in zip(core_levels, lessons)))
    check("a unit's last level carries its dialogue and can-do line",
          all((L.get("dialogue") or []) == les["dialogue"]
              and L.get("can_do") == les["can_do"]
              for L, les in zip(core_levels, lessons)))
    n_notes = sum(len(L.get("notes") or []) for L in core_levels)
    check("the grammar notes ship (%d)" % n_notes,
          n_notes == sum(len(u["notes"]) for u in core["units"]))
    check("every core item is a card with the core's headline",
          all(by_id.get(it["sq"], {}).get("en") == it["en"] for it in items))
    check("every core word ships the core's example",
          all((by_id[it["sq"]].get("ex") or {}).get("sq") == it["ex"]["sq"]
              for it in words))
    check("phrases are marked, and only phrases",
          {w["id"] for w in flat if w.get("phrase")}
          == {it["sq"] for it in phrases})
    is_form = re.compile(r"\(from [^()]+, [^()]+\)$")
    check("no core card is an inflected form of another card",
          not [it["sq"] for it in items if is_form.search(by_id[it["sq"]]["en"])])
    # do and ka keep reviewed function-word cards of their own.
    left = sorted(w["sq"] for w in flat if is_form.search(w["en"]))
    check("form cards are gone from the whole deck but %s" % left,
          left == ["do", "ka"])
    order = {}
    for w in flat:
        order.setdefault(w["level"], []).append((w["ord"], w["id"]))
    check("the flat index keeps each core level's teaching order",
          all([i for _, i in sorted(order[L["level"]])]
              == [w["sq"] for w in L["words"]] for L in core_levels))

print()
if failures:
    print("FAILURES (%d):" % len(failures))
    for f in failures:
        print("  x " + f)
    sys.exit(1)
print("ALL CONVERSATION-CORE CHECKS PASSED")
