#!/usr/bin/env python3
"""Fetch the remaining human-translated en<->sq corpora, HPLT included."""
import sys, time, urllib.request, zipfile
from pathlib import Path

BASE = "https://object.pouta.csc.fi/OPUS-{corpus}/{version}/moses/en-sq.txt.zip"
# Three parents up: this file is tools/corpus/fetch_more.py, so the repo root
# (and therefore src_raw/opus, where select_examples.py reads from) is three
# levels up. parent.parent lands on tools/ and is a directory nothing reads.
DEST = Path(__file__).resolve().parent.parent.parent / "src_raw" / "opus"
CORPORA = [
    ("bible-uedin", "v1"),
    ("ELRC-3052-wikipedia_health", "v1"),
    ("MaCoCu", "v2"),
    ("HPLT", "v3"),
]
UA = {"User-Agent": "albcourse/1.0 (+albanian srs course)"}


def fetch(corpus, version):
    DEST.mkdir(parents=True, exist_ok=True)
    url = BASE.format(corpus=corpus, version=version)
    tpath = DEST / (corpus + ".txt")
    part = DEST / (corpus + ".part")
    if tpath.exists() and tpath.stat().st_size > 0:
        print("  cached", flush=True)
        return tpath
    print("  GET " + url, flush=True)
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=900) as resp:
            total = int(resp.headers.get("content-length", 0))
            got = 0
            with open(part, "wb") as fh:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    fh.write(chunk)
                    got += len(chunk)
                    print("    %d%%" % (100 * got // total), end="\r", flush=True)
        print()
    except Exception as exc:
        part.unlink(missing_ok=True)
        print("  FAILED " + str(exc), file=sys.stderr)
        return None
    try:
        with zipfile.ZipFile(part) as zf:
            names = zf.namelist()
            en_m = next(n for n in names if n.endswith(".en"))
            sq_m = next(n for n in names if n.endswith(".sq"))
            with zf.open(en_m) as ef, zf.open(sq_m) as sf:
                out = open(tpath, "w", encoding="utf-8")
                for el, sl in zip(ef, sf):
                    e = el.decode("utf-8", "replace").strip()
                    s = sl.decode("utf-8", "replace").strip()
                    if e and s:
                        out.write(e + "\t" + s + "\n")
                out.close()
    except Exception as exc:
        print("  unzip failed " + str(exc), file=sys.stderr)
        return None
    finally:
        part.unlink(missing_ok=True)
    print("  %d MB in %.0fs" % (tpath.stat().st_size // (1 << 20), time.time() - t0), flush=True)
    return tpath


def main():
    for corpus, version in CORPORA:
        print("== " + corpus, flush=True)
        fetch(corpus, version)


if __name__ == "__main__":
    main()
