#!/usr/bin/env python3
"""Guard the example-coverage invariant.

A first attempt at example ranking hard-rejected any example that did not
literally contain the headword token. That silently cost 149 cards their only
example - including good ones like "Eshte e bukur." for jam and "Une di. Une
s'di." for se - and it was invisible because nothing asserted coverage.

Ranking exists to make a sentence better, never to make one disappear. This
test pins that: the number of cards shipping an example may not fall below the
known floor, and the ranker may never drop an example it was handed.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from example_rank import rank_examples, score_example  # noqa: E402

# Cards with an example before this work started, measured on main.
BASELINE_WITH_EXAMPLE = 383

failures = []


def check(cond, name, extra=""):
    if cond:
        print(f"  ok {name}")
    else:
        print(f"  x  {name}" + (f"  [{extra}]" if extra else ""))
        failures.append(name)


def main():
    print("example coverage tests")

    words = json.loads((ROOT / "data" / "words.json").read_text(encoding="utf-8"))["words"]
    with_ex = [w for w in words if w.get("ex")]

    check(
        len(with_ex) >= BASELINE_WITH_EXAMPLE,
        "coverage did not fall below the measured baseline",
        f"{len(with_ex)} < {BASELINE_WITH_EXAMPLE}",
    )
    check(len(words) == 3731, "deck still holds every card", str(len(words)))

    # The ranker must never drop an example it was handed.
    freq = {"te": (1, 10), "dhe": (2, 10), "unaz": (3, 10), "jam": (4, 10)}
    handed = [
        {"sq": "dhe fshat", "en": "and the village"},
        {"sq": "mish vice", "en": "beef"},
        {"sq": "marr shume fjale nga libri githe", "en": "takes many words"},
    ]
    kept = rank_examples(handed, "dhe", 2, freq)
    check(len(kept) == len(handed), "rank_examples drops nothing", f"{len(kept)} of {len(handed)}")

    # Only genuinely unusable text scores zero.
    check(score_example({"sq": "", "en": "x"}, "dhe", 2, freq) == 0, "empty Albanian scores 0")
    check(score_example({"sq": "dhe fshat", "en": ""}, "dhe", 2, freq) == 0, "missing English scores 0")
    check(score_example({"sq": "mish vice", "en": "beef"}, "mish", 2, freq) > 0,
          "a compound fragment is penalised, not dropped")

    # Ordering: a short, familiar, on-headword sentence beats a long one with
    # rare filler. This is the behaviour the learner actually asked for.
    good = {"sq": "Une jam shume i lumtur.", "en": "I am very happy."}
    bad = {
        "sq": "Ai merr shume fjale nga libri githe korniza e madhe e shkolles sone te vjeter.",
        "en": "He takes many words from the whole big cover of my old school.",
    }
    rank = 5
    check(score_example(good, "shume", rank, freq) > score_example(bad, "shume", rank, freq),
          "short familiar sentence outranks long rare-filler one")
    check(score_example(good, "shume", rank, freq) > score_example({"sq": "shume", "en": "a lot"}, "shume", rank, freq),
          "a real sentence outranks a bare headword fragment")
    check(score_example({"sq": "Ai nuk mban syze.", "en": "He has no eyes."}, "nuk", 3, freq) > 0,
          "a clitic-heavy sentence still scores")

    print()
    if failures:
        print(f"{len(failures)} FAILED")
        return 1
    print("EXAMPLE COVERAGE VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
