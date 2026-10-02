#!/usr/bin/env python3
"""Download en<->sq parallel corpora from OPUS into src_raw/opus/.

Large machine-translated corpora (NLLB, CCMatrix, CCAligned, OpenSubtitles)
are deliberately excluded: MT output teaches the learner wrong sentences, which
is the one failure mode we cannot detect automatically.
"""
from __future__ import annotations

import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://object.pouta.csc.fi/OPUS-{corpus}/{version}/moses/en-sq.txt.zip"
# This file is tools/corpus/fetch_opus.py, so THREE parents up is the repo root.
# parent.parent lands on tools/ and resolves to tools/src_raw/opus, a directory
# select_examples.py never reads (it uses <repo>/src_raw/opus), so the corpora
# downloaded to the wrong place and the selector still ran on 3 of 11.
DEST = Path(__file__).resolve().parent.parent.parent / "src_raw" / "opus"

# (corpus, version, api_pair_count, human_translated)
CORPORA = [
    ("Tatoeba", "v2026-07-08", 1104, True),
    ("EUbookshop", "v2", 3, True),
    ("TildeMODEL", "v2018", None, True),
    ("GlobalVoices", "v2018q4", None, True),
    ("TED2020", "v1", 69896, True),
    ("QED", "v2.0a", 117215, True),
    ("GNOME", "v1", 151012, True),
    ("WikiMatrix", "v1", 180112, False),
    ("wikimedia", "v20260327", 236020, False),
    ("Tanzil", "v1", 368134, False),
    ("SETIMES", "v2", 227516, True),
]

UA = {"User-Agent": "albcourse/1.0 (+albanian srs course)"}


def fetch(corpus, version):
    """Download and extract one corpus zip. Returns path to extracted .txt or None."""
    DEST.mkdir(parents=True, exist_ok=True)
    url = BASE.format(corpus=corpus, version=version)
    tpath = DEST / (corpus + ".txt")
    part = DEST / (corpus + ".part")

    if tpath.exists() and tpath.stat().st_size > 0:
        print("  cached, " + str(round(tpath.stat().st_size / 1e6, 1)) + " MB")
        return tpath

    print("  GET " + url)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=300) as resp:
            total = int(resp.headers.get("content-length", 0))
            got = 0
            with open(part, "wb") as fh:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    fh.write(chunk)
                    got += len(chunk)
                    print("    " + str(int(100 * got / total)) + "%", end="\r")
        print("")
    except urllib.error.HTTPError as exc:
        part.unlink(missing_ok=True)
        print("  HTTP " + str(exc.code) + " " + str(exc.reason), file=sys.stderr)
        return None
    except Exception as exc:
        part.unlink(missing_ok=True)
        print("  FAILED " + str(exc), file=sys.stderr)
        return None

    try:
        with zipfile.ZipFile(part) as zf:
            members = zf.namelist()
            en_m = next(n for n in members if n.endswith(".en"))
            sq_m = next(n for n in members if n.endswith(".sq"))
            with zf.open(en_m) as ef, zf.open(sq_m) as sf, open(tpath, "w", encoding="utf-8") as dst:
                for en_line, sq_line in zip(ef, sf):
                    en = en_line.decode("utf-8", "replace").strip()
                    sq = sq_line.decode("utf-8", "replace").strip()
                    if en and sq:
                        dst.write(en + "\t" + sq + "\n")
    except Exception as exc:
        print("  unzip failed " + str(exc), file=sys.stderr)
        return None
    finally:
        part.unlink(missing_ok=True)

    print("  " + str(round(tpath.stat().st_size / 1e6, 1)) + " MB extracted")
    return tpath


def main():
    ok, fail = 0, 0
    for corpus, version, pairs, human in CORPORA:
        tag = "human" if human else "other"
        print("[" + tag + "] " + corpus + " (api reported " + str(pairs) + " pairs)")
        t0 = time.time()
        if fetch(corpus, version) is not None:
            ok += 1
        else:
            fail += 1
        print("  took " + str(round(time.time() - t0, 1)) + "s")
    used = sum(f.stat().st_size for f in DEST.glob("*") if f.is_file())
    print("")
    print("fetched " + str(ok) + " ok, " + str(fail) + " failed")
    print("on disk: " + str(round(used / 1e6, 1)) + " MB")


if __name__ == "__main__":
    main()
