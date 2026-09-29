#!/usr/bin/env python3
"""Build data/words.json - a compact index of every card.

The level files carry full sense detail, etymology and category dumps, which is
right for a lesson view but too heavy to load 543 times over. This flattens the
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

# Reference sentences mined from human-translated parallel corpora (OPUS).
# Wiktionary examples always win: they are authored for the headword and
# aligned to the exact sense. This file only fills gaps. See
# tools/select_examples.py for the selection gates and their rationale.
CORPUS_EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / "data" / "corpus_examples.json"


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


def sense_pair(word):
    """Pick the (gloss, example) pair a card should show, or None.

    Returns the example plus a flag saying whether it came from the headline
    sense or from a sibling sense of the same part of speech, so the app can
    label a borrowed example instead of presenting it as if it illustrated the
    headline gloss.

    This MUST match examplePairForSense() in app/js/course.js, which applies the
    same rule to the lesson view. They drifted apart once: the Python version
    scanned every sense and returned the first example found, so the review
    card kept showing the bug the lesson view had already fixed. For "e" -
    headline "and", whose conjunction senses have no examples - it reached into
    the preposition sense "of, + dative" and put "The honor of an Albanian
    can not be sold or bought in a bazaar." under "and".

    The rule: a card shows ONE gloss, so the example must illustrate THAT
    gloss. Preference order:
      1. an example on the headline sense itself
      2. an example on another sense of the SAME part of speech

    A different part of speech is never borrowed: pairing a conjunction gloss
    with a preposition sentence is the exact bug above. When the headline sense
    has no example the card keeps its gloss and simply shows no sentence, which
    is honest.

    Wiktionary holds examples for only 955 Albanian headwords, so most cards
    genuinely have none. That is a limit of the source, not a defect, and must
    not be papered over with invented sentences.
    """
    senses = word.get("sense_detail") or []
    if not senses:
        return None

    home = senses[0]

    def usable(sense):
        out = []
        for ex in sense.get("examples") or []:
            if (
                isinstance(ex, dict)
                and isinstance(ex.get("sq"), str)
                and ex["sq"].strip()
                and isinstance(ex.get("en"), str)
                and ex["en"].strip()
            ):
                out.append({"sq": ex["sq"].strip(), "en": ex["en"].strip()})
        return out

    own = usable(home)
    if own:
        return {"ex": own[0], "from_sense": False, "sense_gloss": None}

    pos = home.get("pos")
    for sense in senses[1:]:
        if sense.get("pos") != pos:
            continue
        same = usable(sense)
        if same:
            return {
                "ex": same[0],
                "from_sense": True,
                "sense_gloss": sense.get("gloss"),
            }
    return None


def _slim(ex):
    """Reduce a corpus record to the two fields a card actually shows."""
    if not ex or not ex.get("sq") or not ex.get("en"):
        return None
    return {"sq": ex["sq"], "en": ex["en"]}


def main():
    files = sorted(LEVELS.glob("level_*.json"))
    if not files:
        print(f"no level files in {LEVELS}")
        return 1

    corpus = {}
    if CORPUS_EXAMPLES.exists():
        corpus = json.loads(CORPUS_EXAMPLES.read_text(encoding="utf-8"))
        print("corpus examples available: %d" % len(corpus))
    else:
        print("no corpus_examples.json -- Wiktionary examples only")

    words = []
    for path in files:
        level = json.loads(path.read_text(encoding="utf-8"))
        for w in level["words"]:
            pair = sense_pair(w)
            words.append(
                {
                    "id": w.get("id") or w["sq"],
                    "sq": w["sq"],
                    "en": w["en"],
                    "rank": w.get("rank"),
                    "level": w.get("level") or level.get("level"),
                    "family": w.get("family"),
                    "is_root": bool(w.get("is_root")),
                    # A card never ships a repeated label like
                    # ["conjunction", "conjunction"] and the card would
                    # render the label twice. Dedup, then cap at 2.
                    "pos": dedup_labels(w)[:2],
                    "etymology_class": w.get("etymology_class"),
                    "components": w.get("components") or [],
                    # Wiktionary first; corpus only fills a genuine gap.
                    # Only sq/en ship. The corpus record also carries
                    # "corpus" and "score", which are build-time provenance
                    # the app never reads; leaking them bloats every card.
                    "ex": (pair["ex"] if pair else _slim(corpus.get(w["sq"]))),
                    # Set when the example came from a sibling sense of the
                    # same POS, so the app can show that sense's gloss and the
                    # sentence is never read as illustrating the headline gloss.
                    "ex_gloss": (pair or {}).get("sense_gloss"),
                    "ex_from_sense": bool((pair or {}).get("from_sense")),
                }
            )

    words.sort(key=lambda d: (d.get("rank") or 0))

    out = DATA / "words.json"
    out.write_text(
        json.dumps(
            {"version": 1, "count": len(words), "words": words},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {out.relative_to(ROOT)}: {len(words)} words from {len(files)} levels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
