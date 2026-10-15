#!/usr/bin/env python3
"""Affix patterns: the small set of Albanian affixes worth teaching.

Most of the deck is opaque roots and loans, so affixes connect a few hundred
words, not the whole course. An affix earns a pattern note only if it passes
all four of the usual tests for teaching an affix (Bauer & Nation's affix
levels):

  * frequent      -- at least MIN_EXAMPLES transparent derivations in the deck;
  * predictable   -- the meaning of the whole follows from the parts;
  * regular       -- few spelling variants, all listed here;
  * unconfusable  -- or, where it collides with an inflection (-im is also
                     "we ..."), the note says so out loud.

Prefixes such as mos-, ri-, mbi-, nën-, kundër- and bashkë- fail the first
test on this deck (1-3 derivations each); për-, sh- and ç- fail the second
(përdor "use" is për- + dorë "hand", which nobody can guess). They still
appear in a word's breakdown -- marked as historical -- but are not taught.

Breakdowns come only from the etymology parser (build_course.components_of),
never from spelling: 220 deck words start with sh- and almost none are
built with the prefix.

This module does two jobs:

  annotate_levels(levels)   enrich components and attach pattern notes; the
                            build calls it before writing the level files.
  main()                    re-derive components from the etymologies the
                            shipped level files already carry and rewrite
                            them in place, for when the Kaikki dump is not
                            available for a full rebuild. Levels do not move.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
LEVELS_DIR = os.path.join(DATA, "levels")

# A pattern is introduced at the level of its Nth transparent example: the
# learner has met a few words built this way and the note names the pattern
# they have been seeing, rather than front-loading an abstract item.
MIN_EXAMPLES = 3
PATTERN_EXAMPLES = 4

# id -> pattern. `forms` are every spelling the parser may report (without
# the hyphen); `meaning` is the short label on the breakdown; `note` is the
# warning a learner needs so the pattern does not mislead them.
AFFIXES = {
    "im": {
        "kind": "suffix", "forms": ["im"],
        "label": "-im", "meaning": "the act of (noun)",
        "summary": "Turns a verb into the noun for doing it: mendoj (to think) "
                   "→ mendim (thought).",
        "note": "-im is also the 'we' ending on verbs: flasim = we speak, "
                "ishim = we were. A word in -im is only a noun if a verb "
                "in -oj/-ej sits behind it.",
    },
    "je": {
        "kind": "suffix", "forms": ["je"],
        "label": "-je", "meaning": "the act of (noun)",
        "summary": "Turns a verb into the noun for doing it, mostly verbs "
                   "that do not end in -oj: lidh (to tie) → lidhje "
                   "(connection).",
        "note": "Not every word ending in -je is built this way: anije "
                "(ship) is not.",
    },
    "si": {
        "kind": "suffix", "forms": ["si", "ësi"],
        "label": "-(ë)si", "meaning": "-ness, -ity",
        "summary": "Turns an adjective into a quality: shpejt (fast) → "
                   "shpejtësi (speed), mirë (good) → mirësi (goodness).",
        "note": "Spelled -ësi after most consonants and -si after a vowel "
                "(njësi). Not the same word as si (how, like).",
    },
    "shem": {
        "kind": "suffix", "forms": ["shëm", "shme"],
        "label": "-shëm", "meaning": "-ful, -able",
        "summary": "Makes an adjective from a noun or verb: fuqi (strength) → "
                   "i fuqishëm (powerful), kuptoj (to understand) → i "
                   "kuptueshëm (understandable).",
        "note": "The feminine is -shme (e fuqishme). After a verb in -oj it "
                "becomes -ueshëm.",
    },
    "tar": {
        "kind": "suffix", "forms": ["tar", "tare"],
        "label": "-tar", "meaning": "person / of",
        "summary": "A person who deals with something, or an adjective "
                   "'of it': këngë (song) → këngëtar (singer), komb (nation) "
                   "→ kombëtar (national).",
        "note": "Often -ëtar after a consonant. The feminine is -tare "
                "(këngëtare, shqiptare).",
    },
    "isht": {
        "kind": "suffix", "forms": ["isht"],
        "label": "-isht", "meaning": "-ly",
        "summary": "Turns an adjective into an adverb: zyrtar (official) → "
                   "zyrtarisht (officially).",
        "note": "It also names languages: gjermanisht = (in) German, "
                "kinezisht = (in) Chinese.",
    },
    "ues": {
        "kind": "suffix", "forms": ["ues", "uese"],
        "label": "-ues", "meaning": "one who does it",
        "summary": "The person who does a verb in -oj: mësoj (to teach) → "
                   "mësues (teacher), lexoj (to read) → lexues (reader).",
        "note": "The feminine is -uese (mësuese). Do not confuse it with "
                "-ueshëm (-able), which is -shëm on the same stem.",
    },
    "pa": {
        "kind": "prefix", "forms": ["pa"],
        "label": "pa-", "meaning": "un-, without",
        "summary": "Negates a word: fund (end) → pafund (endless), dukshëm "
                   "(visible) → padukshëm (invisible).",
        "note": "pa is also the preposition 'without' (pa ty = without you). "
                "Many words just start with pa- by chance: palloj (to beat) "
                "has nothing to do with lloj.",
    },
    "zh": {
        "kind": "prefix", "forms": ["zh"],
        "label": "zh-", "meaning": "undo",
        "summary": "Reverses a verb: vesh (to dress) → zhvesh (to undress).",
        "note": "Most words that start with zh- are not built this way.",
    },
}

# Endings that carry no meaning of their own (pabesë = pa- + besë + -ë), so
# they neither need teaching nor stop a breakdown being transparent.
NEUTRAL_SUFFIXES = frozenset({"ë"})

# The word a derivation is built on: "stem" after a prefix, "base" before a
# suffix (see build_course.components_of for why they differ).
LEXICAL = ("stem", "base")

FORM_TO_ID = {}
for _id, _a in AFFIXES.items():
    for _f in _a["forms"]:
        FORM_TO_ID[(_a["kind"], _f)] = _id

# Derivations whose meaning a learner can work out from the parts, reviewed by
# hand. Anything not listed is shown as a historical breakdown: still a memory
# aid, but never offered as "guess from the parts". The default is deliberately
# the safe one -- a word added by a rebuild stays historical until reviewed.
#
# Left out on purpose, so the reasons are on record:
#   meaning drifted   mundim (can -> strain), mundje (can -> defeat),
#                     sëmundje, qëllim (hit -> goal), sjellje / sjellshëm
#                     (bring -> behaviour / polite), anëtar (side -> member),
#                     zotësi, gjithësi, bashkësi, rrokje, çështje, patjetër,
#                     pafe, mëparshëm, dështim, zhvendos, zhvilloj
#   stem is glossed   pije (pi: "from"), dukshëm / zhduk (duk: "virtue"),
#   with the wrong    ndjeshëm (ndjej: "forgive"), qetësi (qetë: a verb form),
#   homograph         shëndetshëm (shëndet: "bless you!"), rëndësishëm
#                     (rëndësi: "heaviness")
TRANSPARENT = frozenset("""
mendim vendim besim kuptim kalim shikim dëgjim bashkim vizatim gabim qetësim
mësim premtim takim ushqim urim ndryshim fitim afrim shkrim pranim pushim
festim ndalim lexim kafshim ushtrim përfundim përkthim përqafim përshkrim
përcaktim drejtim dyshim ndërtim zbulim shpëtim krahasim shpjegim çmim supozim
kujtim shërbim lëndim veprim argëtim burim shënim shkëmbim këmbim njoftim
vrapim sqarim përjashtim shqetësim ndikim vëzhgim këshillim tentim dallim
zemërim bekim rekomandim motivim zgjim përfitim izolim zhvillim shtrembërim
udhëzim rrënim masturbim asgjësim incizim dëbim
mendje dukje vdekje vendosje folje lidhje humbje vrasje lëvizje hapje zgjidhje
lindje qeshje dhembje goditje zgjedhje hyrje përhapje ndeshje puthje shfaqje
mbledhje shëtitje heshtje djegje udhëheqje tallje mbështetje shprehje lutje
çarje vuajtje zhdukje shtirje zhvendosje
mirësi mundësi shpejtësi madhësi fatkeqësi lartësi miqësi qartësi ftohtësi
nxehtësi mbarësi aftësi ndjesi njësi mendjemadhësi risi tërësi afërsi kënaqësi
popullsi
domosdoshëm gatshëm nevojshëm kujdesshëm kuptueshëm arsyeshëm paarsyeshëm
mrekullueshëm shkëlqyeshëm fuqishëm mëshirshëm adhurueshëm vetëdijshëm
ngjashëm natyrshëm yndyrshëm
kujdestar tregtar qytetar luftëtar dijetar lajmëtar këngëtar kryetar zyrtar
gënjeshtar udhëtar kombëtar shqiptar shqiptare këshilltar vullnetar
shkencëtar qeveritar gjahtar
domosdoshmërisht qartësisht absolutisht përgjithësisht zyrtarisht kinezisht
verbërisht gjermanisht seksualisht historikisht psikologjikisht
mësues lexues përfaqësues vëzhgues
pafund pakujdesshëm pakuptim pakuptueshëm panjohur parregullt pabesë
padukshëm padrejtësi
zhdukem zhvesh
""".split())


def short_gloss(text):
    """The first sense of a gloss, for a breakdown label: 'can, to be able
    to; ...' -> 'can'."""
    text = (text or "").split(";")[0].split(",")[0].strip()
    return text[:40]


def affix_id(comp):
    return FORM_TO_ID.get((comp.get("role"), comp.get("word")))


def enrich(word, gloss_of):
    """Annotate one card's components in place and set its breakdown kind.

    Each component gains `en` (a stem or base's short gloss) or `affix`/`meaning`
    (a taught affix). `breakdown` is "transparent" when the parts predict
    the meaning, "historical" otherwise, and absent when there is nothing
    to break down.
    """
    comps = word.get("components") or []
    if not comps:
        word.pop("breakdown", None)
        return
    for c in comps:
        for k in ("en", "affix", "meaning"):
            c.pop(k, None)
        if c["role"] in LEXICAL:
            g = short_gloss(gloss_of.get(c["word"]))
            if g:
                c["en"] = g
        else:
            aid = affix_id(c)
            if aid:
                c["affix"] = aid
                c["meaning"] = AFFIXES[aid]["meaning"]
    has_stem = any(c["role"] in LEXICAL for c in comps)
    taught = all(c["role"] in LEXICAL or c.get("affix")
                 or (c["role"] == "suffix" and c["word"] in NEUTRAL_SUFFIXES)
                 for c in comps)
    has_affix = any(c.get("affix") for c in comps)
    word["breakdown"] = ("transparent"
                         if has_stem and taught and has_affix
                         and word["sq"] in TRANSPARENT
                         else "historical")
    if word["breakdown"] == "historical":
        # A historical stem gloss is often the wrong homograph or a long-lost
        # sense (pi "from", duk "virtue"). Showing it would teach the error.
        for c in comps:
            c.pop("en", None)


def annotate_levels(levels):
    """Enrich every card, then attach pattern notes. Levels are in order.

    Each level that introduces a pattern gets `patterns`: a list of
    {id, label, meaning, summary, note, examples:[{sq, en, stem, stem_en}]}.
    Returns {affix_id: level} for the patterns that were placed.
    """
    gloss_of = {w["sq"]: w.get("en", "") for lvl in levels for w in lvl["words"]}
    seen = {aid: [] for aid in AFFIXES}
    placed = {}
    for lvl in levels:
        lvl.pop("patterns", None)
        for w in lvl["words"]:
            enrich(w, gloss_of)
        new_here = []
        for w in lvl["words"]:
            if w.get("breakdown") != "transparent":
                continue
            stem = next(c for c in w["components"] if c["role"] in LEXICAL)
            for c in w["components"]:
                aid = c.get("affix")
                if not aid:
                    continue
                seen[aid].append({"sq": w["sq"], "en": short_gloss(w["en"]),
                                  "stem": stem["word"],
                                  "stem_en": stem.get("en", "")})
                if len(seen[aid]) == MIN_EXAMPLES and aid not in placed:
                    placed[aid] = lvl["level"]
                    new_here.append(aid)
        if new_here:
            lvl["patterns"] = [_pattern(aid, seen[aid][:PATTERN_EXAMPLES])
                               for aid in new_here]
    return placed


def _pattern(aid, examples):
    a = AFFIXES[aid]
    return {"id": aid, "label": a["label"], "meaning": a["meaning"],
            "summary": a["summary"], "note": a["note"],
            "examples": examples}


def main():
    """Re-derive breakdowns on the shipped level files, in place."""
    sys.path.insert(0, HERE)
    import build_course as bc

    files = sorted(f for f in os.listdir(LEVELS_DIR)
                   if f.startswith("level_") and f.endswith(".json"))
    levels = []
    for f in files:
        with open(os.path.join(LEVELS_DIR, f), encoding="utf-8") as fh:
            levels.append((f, json.load(fh)))
    levels.sort(key=lambda t: t[1]["level"])
    words = {w["sq"] for _, lvl in levels for w in lvl["words"]}
    for _, lvl in levels:
        for w in lvl["words"]:
            w["components"] = [{"word": x, "role": r} for x, r in
                               bc.components_of(w.get("etymology") or "", words)]
    placed = annotate_levels([lvl for _, lvl in levels])
    for f, lvl in levels:
        with open(os.path.join(LEVELS_DIR, f), "w", encoding="utf-8") as fh:
            json.dump(lvl, fh, ensure_ascii=False, indent=1)

    for name in ("course.json", "index.json"):
        path = os.path.join(DATA, name)
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        entries = doc["levels"] if name == "course.json" else doc
        set_index_patterns(entries, placed)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)

    n = {k: sum(1 for _, l in levels for w in l["words"]
                if w.get("breakdown") == k)
         for k in ("transparent", "historical")}
    print("breakdowns: %(transparent)d transparent, %(historical)d historical"
          % n)
    for aid, lv in sorted(placed.items(), key=lambda t: t[1]):
        print("  pattern %-6s introduced at L%d" % (AFFIXES[aid]["label"], lv))
    skipped = sorted(set(AFFIXES) - set(placed))
    if skipped:
        print("  not taught (fewer than %d transparent examples): %s"
              % (MIN_EXAMPLES, ", ".join(AFFIXES[a]["label"] for a in skipped)))
    return 0


def set_index_patterns(entries, placed):
    """Mark the level-map entries that introduce a pattern."""
    by_level = {}
    for aid, lv in placed.items():
        by_level.setdefault(lv, []).append(AFFIXES[aid]["label"])
    for e in entries:
        e.pop("patterns", None)
        if e["level"] in by_level:
            e["patterns"] = sorted(by_level[e["level"]])


if __name__ == "__main__":
    raise SystemExit(main())
