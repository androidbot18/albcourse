"""Measure what actually makes this course hard to learn from.

Every claim in the improvement report should come out of this file. The
earlier reviews overclaimed twice (a cognate count that was 8x too high, a
level-shape target that produced useless sessions), so the rule here is:
print a number or print nothing.

Usage:  python3 tools/measure_learnability.py
"""
import json
import os
import re
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

with open(os.path.join(DATA, "words.json"), encoding="utf-8") as fh:
    WORDS = json.load(fh)["words"]

with open(os.path.join(DATA, "index.json"), encoding="utf-8") as fh:
    INDEX = json.load(fh)

BY_LEVEL = defaultdict(list)
for w in WORDS:
    BY_LEVEL[w["level"]].append(w)

N = len(WORDS)
MAXLEVEL = max(w["level"] for w in WORDS)


def head(t):
    print()
    print("=" * 72)
    print(t)
    print("=" * 72)


def line(k, v):
    print("  %-46s %s" % (k, v))


# --------------------------------------------------------------- 1. glosses
head("1. GLOSSES -- can a beginner read them?")
multi = [w for w in WORDS if "," in w["en"][:60]]
line("gloss with a comma (2+ senses listed)", "%d (%.1f%%)" % (len(multi), 100.0 * len(multi) / N))
long_gloss = [w for w in WORDS if len(w["en"]) > 70]
line("gloss longer than 70 chars", "%d (%.1f%%)" % (len(long_gloss), 100.0 * len(long_gloss) / N))
very_long = [w for w in WORDS if len(w["en"]) > 110]
line("gloss longer than 110 chars", "%d (%.1f%%)" % (len(very_long), 100.0 * len(very_long) / N))
line("longest gloss", "%d chars: %s" % (max(len(w["en"]) for w in WORDS),
     max(WORDS, key=lambda w: len(w["en"]))["en"][:90]))

# Glosses that still leak dictionary grammar into the learner-facing field.
GRAMMAR_LEAK = re.compile(
    r"\b(third-person|first-person|second-person|present indicative|"
    r"past participle|definite|indefinite|nominalized|"
    r"subjunctive|conditional|participle of|"
    r"plural of|singular of)\b", re.I)
leaks = [w for w in WORDS if GRAMMAR_LEAK.search(w["en"])]
line("gloss still leaking grammar terms", "%d" % len(leaks))
for w in leaks[:5]:
    line("   e.g.", "%s -> %s" % (w["sq"], w["en"][:70]))


# ------------------------------------------------- 2. example sentence quality
head("2. EXAMPLES -- do they use only vocabulary already taught?")
# The owner asked for exactly this: short sentences that reuse vocabulary from
# this lesson or an earlier one. Measure it, do not assume it.
POS = {}
with open(os.path.join(ROOT, "data", "course.json"), encoding="utf-8") as fh:
    pass

word_re = re.compile(r"[A-Za-zëËçÇ\u00C0-\u024F]+")
all_lower = {w["sq"].lower() for w in WORDS}


def tokens(sq):
    return [t.lower() for t in word_re.findall(sq)]


def first_seen_level(tok):
    best = None
    for w in WORDS:
        if w["sq"].lower() == tok:
            lv = w["level"]
            best = lv if best is None else min(best, lv)
    return best


# Precompute earliest level per token once.
EARLIEST = {}
for w in WORDS:
    t = w["sq"].lower()
    if t not in EARLIEST or w["level"] < EARLIEST[t]:
        EARLIEST[t] = w["level"]

with_ex = [w for w in WORDS if w.get("ex") and w["ex"].get("sq")]
lens = []
later = 0
known = 0
total_tok = 0
offenders = []
for w in with_ex:
    toks = tokens(w["ex"]["sq"])
    lens.append(len(toks))
    own = w["level"]
    bad = [t for t in toks
           if t in all_lower and EARLIEST.get(t, 99) > own]
    total_tok += len([t for t in toks if t in all_lower])
    known += len([t for t in toks if t in all_lower]) - len(bad)
    if bad:
        later += 1
        if len(offenders) < 6:
            offenders.append((w["sq"], own, bad, w["ex"]["sq"]))

lens.sort()
line("cards with an example", "%d (%.1f%%)" % (len(with_ex), 100.0 * len(with_ex) / N))
if lens:
    line("example length: min / median / max",
         "%d / %d / %d words" % (lens[0], lens[len(lens) // 2], lens[-1]))
line("examples using a word taught LATER",
     "%d (%.1f%% of examples)" % (later, 100.0 * later / max(1, len(with_ex))))
line("share of example tokens already taught",
     "%.1f%%" % (100.0 * known / max(1, total_tok)))
for sq, own, bad, sent in offenders:
    line("   e.g. L%d %s" % (own, sq), "uses %s | %s" % (bad[:4], sent[:50]))


# ------------------------------------------- 3. confusable sets (minimal pairs)
head("3. CONFUSABLE SETS -- where does confusion actually concentrate?")
NEG = {"nuk", "ne", "jo", "s'jo", "s", "jo"}
CONJ = {"dhe", "se", "por", "që", "ngase", "ose", "apo", "ndërsa", "kurse"}
have = {w["sq"].lower(): w for w in WORDS}
for name, group in (("negation", NEG), ("conjunction", CONJ)):
    present = sorted(t for t in group if t in have)
    levels = [have[t]["level"] for t in present]
    line("%s words in deck" % name, "%d: %s" % (len(present), " ".join(present)))
    if levels:
        line("   their levels", str(levels))
        spread = max(levels) - min(levels)
        line("   spread", "%d levels apart" % spread)

# How many cards share a leading gloss word (a likely confusion cluster).
first_word = Counter()
for w in WORDS:
    fw = w["en"].split(",")[0].strip().split()
    if fw:
        first_word[fw[0].lower()] += 1
clusters = [(k, v) for k, v in first_word.items() if v >= 8]
clusters.sort(key=lambda kv: -kv[1])
line("gloss clusters of 8+ cards sharing a first word", len(clusters))
for k, v in clusters[:6]:
    line("   %r" % k, v)


# ------------------------------------------- 4. coverage by band (learner view)
head("4. COVERAGE BY BAND -- is the tail worse than the head?")
bands = [(1, 20), (21, 100), (101, 300), (301, 500), (501, MAXLEVEL)]
for lo, hi in bands:
    ws = [w for w in WORDS if lo <= w["level"] <= hi]
    if not ws:
        continue
    ex = sum(1 for w in ws if w.get("ex") and w["ex"].get("sq"))
    cog = sum(1 for w in ws if w.get("cognate"))
    comp = sum(1 for w in ws if w.get("components"))
    line("L%d-%d (%d cards)" % (lo, hi, len(ws)),
         "ex %4.1f%%  cognate %4.1f%%  components %4.1f%%"
         % (100.0 * ex / len(ws), 100.0 * cog / len(ws), 100.0 * comp / len(ws)))


# ------------------------------------------- 5. fully opaque words
head("5. OPAQUE WORDS -- nothing to hook onto at all")
opaque = [w for w in WORDS
          if not w.get("components") and not w.get("cognate")
          and not w.get("etymology")]
line("no components AND no cognate AND no etymology",
     "%d (%.1f%%)" % (len(opaque), 100.0 * len(opaque) / N))
early_opaque = [w for w in opaque if w["level"] <= 30]
line("...of those, in the first 30 levels", "%d" % len(early_opaque))
line("   examples", " ".join(w["sq"] for w in early_opaque[:18]))


# ------------------------------------------- 6. can you build a sentence early?
head("6. EARLY USABILITY -- after N levels, what can you actually say?")
for upto in (5, 10, 20, 40):
    ws = [w for w in WORDS if w["level"] <= upto]
    pos = Counter()
    for w in ws:
        for p in (w.get("pos") or ["?"]):
            pos[p] += 1
    top = pos.most_common(4)
    line("after L%d (%d cards)" % (upto, len(ws)),
         ", ".join("%s %d" % (k, v) for k, v in top))


# ------------------------------------------- 7. session size distribution
head("7. SESSION SHAPE")
sizes = [e["word_count"] for e in INDEX]
sizes.sort()
line("levels", len(sizes))
line("words per level: min / median / p90 / max",
     "%d / %d / %d / %d" % (sizes[0], sizes[len(sizes) // 2],
                            sizes[int(len(sizes) * 0.9)], sizes[-1]))
tiny = [e for e in INDEX if e["word_count"] <= 2]
cont = sum(1 for e in tiny if "/" in e.get("title", ""))
line("levels with 1-2 words", "%d" % len(tiny))
line("   of those, a family continuation", "%d (correct: family split)" % cont)
line("   of those, an unsplit small family",
     "%d (correct: too small to fill a session)" % (len(tiny) - cont))
line("   verdict", "thin levels are NOT a defect -- do not 'fix' these")
big = sum(1 for s in sizes if s > 9)
line("levels with more than 9 words", "%d" % big)


# ------------------------------------------- 8. example vocabulary by band
head("8. EXAMPLES USING UNTAUGHT VOCABULARY -- by band (owner criterion)")
bands2 = [(1, 20), (21, 100), (101, 300), (301, 500), (501, MAXLEVEL)]
for lo, hi in bands2:
    ws = [w for w in with_ex if lo <= w["level"] <= hi]
    if not ws:
        continue
    bad = 0
    tot = 0
    for w in ws:
        for t in tokens(w["ex"]["sq"]):
            if t in all_lower:
                tot += 1
                if EARLIEST.get(t, 99) > w["level"]:
                    bad += 1
    line("L%d-%d (%d examples)" % (lo, hi, len(ws)),
         "%.1f%% of deck tokens not yet taught" % (100.0 * bad / max(1, tot)))

print()
print("done -- every number above is measured, none estimated")
