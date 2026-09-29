#!/usr/bin/env python3
"""Verify the MERGED build is what Pages is actually serving.

The local suite proves the data on disk. This checks the deployed site, which
is the only place a stale CDN copy or a failed deploy would show up.
"""
import json
import re
import sys
import urllib.request

BASE = "https://androidbot18.github.io/albcourse"
UA = {"User-Agent": "albcourse-verify/1.0"}


def get(path):
    req = urllib.request.Request(BASE + path, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    fails = []

    def check(cond, name, extra=""):
        print(("  ok " if cond else "  x  ") + name + ("  [%s]" % extra if extra and not cond else ""))
        if not cond:
            fails.append(name)

    print("live deployment check")

    idx = get("/data/index.json")
    check(len(idx) == 594, "594 levels deployed", len(idx))
    check(idx[-1]["level"] == 594, "last level is 594", idx[-1]["level"])

    words = get("/data/words.json")["words"]
    by = {w["sq"]: w for w in words}
    check(len(words) == 4087, "4087 cards deployed", len(words))

    # The inflected forms that PR #11 added, with their lemma families.
    for w, fam in [("është", "jam"), ("janë", "jam"), ("ke", "kam"), ("këtë", "ky")]:
        card = by.get(w)
        check(card is not None and card.get("family") == fam,
              "form card %s is in family %s" % (w, fam),
              (card or {}).get("family"))

    # The 'e' example must illustrate the conjunction, not the article.
    e = by.get("e") or {}
    ex = (e.get("ex") or {}).get("sq", "")
    check(bool(ex) and " e " in ex, "'e' has an example containing the conjunction", ex)
    check("një e tërë" not in ex, "'e' example is not the article sense", ex)

    # Every deployed example needs both halves.
    bad = [w["sq"] for w in words
           if w.get("ex") and (not w["ex"].get("sq") or not w["ex"].get("en"))]
    check(not bad, "every deployed example has Albanian and English", str(bad[:5]))

    with_ex = [w for w in words if w.get("ex")]
    print("  ..  %d/%d cards have an example (%.1f%%)"
          % (len(with_ex), len(words), 100.0 * len(with_ex) / len(words)))

    # Diacritics must survive the pipeline.
    edia = sum(1 for w in words if re.search(r"[ëË]", w["sq"]))
    cced = sum(1 for w in words if re.search(r"[çÇ]", w["sq"]))
    check(edia > 1500, "ë words deployed intact", edia)
    check(cced > 50, "ç words deployed intact", cced)

    print()
    if fails:
        print("FAILURES: %d" % len(fails))
        return 1
    print("LIVE DEPLOYMENT VERIFIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
