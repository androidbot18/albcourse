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
    # These checks were substring tests once and were VACUOUS -- both passed
    # on the very defect they were written to catch ('...dhe eshte shume e
    # lire.', where that 'e' IS the article). They were then replaced by the
    # selector's context_ok(), but that heuristic only accepts 'e' before a
    # verb or pronoun -- which is the CLITIC 'it' ('e di', I know it) -- and
    # rejects 'e' joining two nouns, the plainest conjunction there is.
    #
    # `e` now ships a reviewed example (tools/gloss_overrides.EXAMPLES), so
    # the check is exact: the deployed sentence is that one.
    sys.path.insert(0, str(ROOT / "tools"))
    import gloss_overrides  # noqa: E402
    _, want_sq, want_en = gloss_overrides.EXAMPLES["e"]
    e = by.get("e") or {}
    ex = e.get("ex") or {}
    check(e.get("en") == "and", "deployed 'e' headlines 'and'", e.get("en"))
    check(ex.get("sq") == want_sq and ex.get("en") == want_en,
          "deployed 'e' example is the reviewed conjunction", ex.get("sq"))

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
