#!/usr/bin/env python3
"""Download the two upstream data files the course is built from.

    python3 tools/fetch_sources.py
    python3 tools/build_course.py

Both files are large and are git-ignored; this script makes the build
reproducible from a clean clone instead of relying on someone having them.

Sources
-------
Kaikki.org
    wiktextract of English Wiktionary, Albanian. Supplies glosses, parts of
    speech, etymology, word-family links and example sentences.
    CC BY-SA 4.0 - https://kaikki.org/dictionary/Albanian/meaning/1/G/

hermitdave/FrequencyWords
    Word frequency list built from OpenSubtitles2018. Supplies the corpus
    ranking that decides level order.
    MIT - https://github.com/hermitdave/FrequencyWords
"""

import os
import sys
import urllib.request
import urllib.error
import hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

SOURCES = [
    (
        "kaikki_albanian.jsonl",
        "https://kaikki.org/dictionary/Albanian/kaikki.org-dictionary-Albanian.jsonl",
    ),
    (
        "sq_50k.txt",
        "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/sq/sq_50k.txt",
    ),
]


def fetch(name, url):
    dest = os.path.join(RAW, name)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print("  = %s already present (%.1f MB)" % (name, os.path.getsize(dest) / 1e6))
        return
    print("  > %s" % url)
    tmp = dest + ".part"
    with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
        total = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
    os.replace(tmp, dest)
    print("    saved %.1f MB" % (total / 1e6))


def main():
    os.makedirs(RAW, exist_ok=True)
    print("fetching course sources...")
    failed = []
    for name, url in SOURCES:
        try:
            fetch(name, url)
        except (urllib.error.URLError, OSError) as e:
            # One bad mirror should not abort the other download.
            print("  ! %s failed: %s" % (name, e))
            failed.append(name)
    if failed:
        print()
        print("FAILED: %s" % ", ".join(failed))
        print("Download them manually into data/raw/ and re-run.")
        return 1
    print()
    print("done - now run: python3 tools/build_course.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
