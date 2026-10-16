#!/usr/bin/env python3
"""Prepare the two upstream data files the course is built from.

    python3 tools/fetch_sources.py            # unpack the pinned snapshots
    python3 tools/build_course.py

    python3 tools/fetch_sources.py --refresh  # download the latest upstream
                                              # files into data/sources/

The sources are treated as static. A pinned snapshot of each is committed
under data/sources/, with its SHA-256 below, and the default mode only
unpacks and verifies it into data/raw/ (git-ignored), with no network. The
build was not reproducible while it fetched Kaikki's weekly "latest": the
same code produced a deck one level different from a few weeks earlier.

Upgrading a source is a deliberate, reviewed change: run --refresh, rebuild,
review the data diff, update the hashes printed by --refresh, and commit
the new snapshot together with the rebuilt data.

Sources
-------
Kaikki.org
    wiktextract of English Wiktionary, Albanian. Supplies glosses, parts of
    speech, etymology, word-family links and example sentences.
    CC BY-SA 4.0 - https://kaikki.org/dictionary/Albanian/meaning/1/G/
    Snapshot: 2026-10-15, 24,262 entries.

hermitdave/FrequencyWords
    Word frequency list built from OpenSubtitles2018. Supplies the corpus
    ranking that decides level order.
    MIT - https://github.com/hermitdave/FrequencyWords
"""

import hashlib
import io
import os
import sys
import urllib.error
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
SOURCES_DIR = os.path.join(ROOT, "data", "sources")

# name in data/raw, snapshot in data/sources, member inside a zip snapshot
# (None for a plain file), SHA-256 of the unpacked file, upstream URL.
SOURCES = [
    (
        "kaikki_albanian.jsonl",
        "kaikki_albanian.jsonl.zip",
        "kaikki.org-dictionary-Albanian.jsonl",
        "7a84eca776ebfac752e7251bb0822edc9cd1701d1d58060d4f8ef4b76a208fcc",
        "https://kaikki.org/dictionary/Albanian/kaikki.org-dictionary-Albanian.jsonl",
    ),
    (
        "sq_50k.txt",
        "sq_50k.txt",
        None,
        "5a6d41243584b9c594b35191e9b5851ff8f9d3571e4ca71efde557a7af8f56b2",
        "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/sq/sq_50k.txt",
    ),
]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def snapshot_bytes(snapshot, member):
    path = os.path.join(SOURCES_DIR, snapshot)
    if member is None:
        with open(path, "rb") as fh:
            return fh.read()
    with zipfile.ZipFile(path) as z:
        return z.read(member)


def unpack(name, snapshot, member, digest):
    """Write the pinned snapshot to data/raw/<name>, verifying its hash."""
    dest = os.path.join(RAW, name)
    if os.path.exists(dest):
        with open(dest, "rb") as fh:
            if sha256(fh.read()) == digest:
                print("  = %s matches the pinned snapshot" % name)
                return
        print("  ! %s differs from the pinned snapshot; replacing it" % name)
    data = snapshot_bytes(snapshot, member)
    got = sha256(data)
    if got != digest:
        raise ValueError("%s: snapshot hash %s, pinned %s" % (snapshot, got, digest))
    with open(dest, "wb") as fh:
        fh.write(data)
    print("  > %s from data/sources/%s (%.1f MB)" % (name, snapshot, len(data) / 1e6))


def refresh(snapshot, member, url):
    """Download the latest upstream file into data/sources/."""
    print("  > %s" % url)
    with urllib.request.urlopen(url, timeout=300) as r:
        data = r.read()
    path = os.path.join(SOURCES_DIR, snapshot)
    if member is None:
        with open(path, "wb") as fh:
            fh.write(data)
    else:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.writestr(member, data)
        with open(path, "wb") as fh:
            fh.write(buf.getvalue())
    print("    saved data/sources/%s; new SHA-256 %s" % (snapshot, sha256(data)))


def main(argv):
    if "--refresh" in argv:
        print("downloading the latest upstream sources...")
        for _, snapshot, member, _, url in SOURCES:
            try:
                refresh(snapshot, member, url)
            except (urllib.error.URLError, OSError) as e:
                print("  ! %s failed: %s" % (snapshot, e))
                return 1
        print()
        print("Update the hashes in tools/fetch_sources.py, then rebuild and")
        print("review the data diff before committing.")
        return 0

    os.makedirs(RAW, exist_ok=True)
    print("unpacking the pinned course sources...")
    for name, snapshot, member, digest, _ in SOURCES:
        try:
            unpack(name, snapshot, member, digest)
        except (OSError, KeyError, ValueError, zipfile.BadZipFile) as e:
            print("  ! %s: %s" % (name, e))
            return 1
    print()
    print("done - now run: python3 tools/build_course.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
