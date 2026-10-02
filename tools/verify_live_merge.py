#!/usr/bin/env python3
"""Verify the MERGED build is what Pages is actually serving.

The local suite proves the data on disk. This checks the deployed site, which
is the only place a stale CDN copy or a failed deploy would show up.
"""
import json
import pathlib
import re
import sys
import urllib.request

BASE = "https://androidbot18.github.io/albcourse"
UA = {"User-Agent": "albcourse-verify/1.0"}
ROOT = pathlib.Path(__file__).resolve().parent.parent

# Reuse the selector's own gate rather than re-implementing a weaker one.
# select_examples.py is guarded by __main__, so importing it is side-effect free.
sys.path.insert(0, str(ROOT / "tools" / "corpus"))
from select_examples import context_ok, article_reading  # noqa: E402


def get(path):
    req = urllib.request.Request(BASE + path, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def local(path):
    """The same artifact as built on disk. This is the source of every total."""
    with open(ROOT / path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    fails = []

    def check(cond, name, extra=""):
        print(("  ok " if cond else "  x  ") + name + ("  [%s]" % extra if extra and not cond else ""))
        if not cond:
            fails.append(name)

    print("live deployment check")

    lidx = local("data/index.json")
    lwords = local("data/words.json")["words"]
    want_levels = len(lidx)
    want_last = lidx[-1]["level"]
    want_edia = sum(1 for w in lwords if re.search(r"[\u00eb\u00cb]", w["sq"]))
    want_cced = sum(1 for w in lwords if re.search(r"[\u00e7\u00c7]", w["sq"]))
    want_ex = sum(1 for w in lwords if w.get("ex"))

    idx = get("/data/index.json")
    check(len(idx) == want_levels, "%d levels deployed" % want_levels, len(idx))
    check(idx[-1]["level"] == want_last, "last level is %d" % want_last, idx[-1]["level"])

    words = get("/data/words.json")["words"]
    by = {w["sq"]: w for w in words}
    check(len(words) == len(lwords), "%d cards deployed" % len(lwords), len(words))

    # The decisive check: the deployed cards ARE the local cards. Counts alone
    # would pass if a deploy dropped a gloss and gained a card elsewhere.
    lby = {w["sq"]: w for w in lwords}
    if len(lby) == len(lwords):
        drift = [sq for sq, w in lby.items() if by.get(sq) != w]
        check(not drift, "deployed cards match the local build", str(drift[:5]))
    else:
        check(False, "local build has no duplicate cards", str(len(lwords) - len(lby)))

    # The inflected forms that PR #11 added, with their lemma families.
    for w, fam in [("është", "jam"), ("janë", "jam"), ("ke", "kam"), ("këtë", "ky")]:
        card = by.get(w)
        check(card is not None and card.get("family") == fam,
              "form card %s is in family %s" % (w, fam),
              (card or {}).get("family"))

    # The 'e' example must illustrate the conjunction, not the article.
    #
    # These two checks used to be substring tests and were VACUOUS -- both
    # passed on the very defect they were written to catch:
    #   check(" e " in ex)     was satisfied by '...dhe eshte shume e lire.',
    #                          where that 'e' IS the article;
    #   check("një e tërë" not in ex)  is satisfied by any sentence lacking
    #                          that one literal phrase, so it could never
    #                          detect the article sense at all.
    # A check that cannot fail is worth nothing. Both are replaced by the SAME
    # context_ok() the selector uses to choose the example, built from the
    # DEPLOYED cards' own POS labels, so the verifier and the build agree on
    # what the conjunction looks like instead of each guessing.
    e = by.get("e") or {}
    ex = (e.get("ex") or {}).get("sq", "")
    if ex:
        pos_index = {}
        for w in words:
            for lab in w.get("pos") or []:
                pos_index.setdefault(w["sq"].lower(), [])
                if lab not in pos_index[w["sq"].lower()]:
                    pos_index[w["sq"].lower()].append(lab)
        check(context_ok(ex, "e", pos_index),
              "deployed 'e' example is a provable conjunction", ex)
        check(not article_reading(ex, "e", pos_index),
              "deployed 'e' example is not the article sense", ex)
    else:
        check(False, "deployed 'e' example is a provable conjunction", "no example")
        check(False, "deployed 'e' example is not the article sense", "no example")

    # Every deployed example needs both halves.
    bad = [w["sq"] for w in words
           if w.get("ex") and (not w["ex"].get("sq") or not w["ex"].get("en"))]
    check(not bad, "every deployed example has Albanian and English", str(bad[:5]))

    with_ex = [w for w in words if w.get("ex")]
    print("  ..  %d/%d cards have an example (%.1f%%); local build has %d"
          % (len(with_ex), len(words), 100.0 * len(with_ex) / len(words), want_ex))
    check(len(with_ex) == want_ex, "deployed example coverage matches the local build",
          "%d vs %d" % (len(with_ex), want_ex))

    # Diacritics must survive the pipeline - as many as the local build has.
    edia = sum(1 for w in words if re.search(r"[ëË]", w["sq"]))
    cced = sum(1 for w in words if re.search(r"[çÇ]", w["sq"]))
    check(edia == want_edia, "%d ë words deployed intact" % want_edia, edia)
    check(cced == want_cced, "%d ç words deployed intact" % want_cced, cced)

    print()
    if fails:
        print("FAILURES: %d" % len(fails))
        return 1
    print("LIVE DEPLOYMENT VERIFIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
