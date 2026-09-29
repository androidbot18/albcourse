#!/usr/bin/env python3
"""Probe candidate Albanian sentence-pair sources: size + reachability.

Read-only. Nothing is downloaded at full size here -- we only HEAD the
archive so we know what a real fetch would cost before spending disk.
"""
import urllib.error
import urllib.request

SOURCES = {
    "Tatoeba": "https://object.pouta.csc.fi/OPUS-Tatoeba/v2026-07-08/moses/en-sq.txt.zip",
    "GlobalVoices": "https://object.pouta.csc.fi/OPUS-GlobalVoices/v2018q4/moses/en-sq.txt.zip",
    "TildeMODEL": "https://object.pouta.csc.fi/OPUS-TildeMODEL/v2018/moses/en-sq.txt.zip",
    "EUbookshop": "https://object.pouta.csc.fi/OPUS-EUbookshop/v2/moses/en-sq.txt.zip",
    "TED2020": "https://object.pouta.csc.fi/OPUS-TED2020/v1/moses/en-sq.txt.zip",
    "GNOME": "https://object.pouta.csc.fi/OPUS-GNOME/v1/moses/en-sq.txt.zip",
    "WikiMatrix": "https://object.pouta.csc.fi/OPUS-WikiMatrix/v1/moses/en-sq.txt.zip",
    "wikimedia": "https://object.pouta.csc.fi/OPUS-wikimedia/v20260327/moses/en-sq.txt.zip",
    "Tanzil": "https://object.pouta.csc.fi/OPUS-Tanzil/v1/moses/en-sq.txt.zip",
    "QED": "https://object.pouta.csc.fi/OPUS-QED/v2.0a/moses/en-sq.txt.zip",
    "MaCoCu": "https://object.pouta.csc.fi/OPUS-MaCoCu/v2/moses/en-sq.txt.zip",
    "OpenSubtitles": "https://object.pouta.csc.fi/OPUS-OpenSubtitles/v2024/moses/en-sq.txt.zip",
    "CCAligned": "https://object.pouta.csc.fi/OPUS-CCAligned/v1/moses/en-sq.txt.zip",
    "SETIMES": "https://object.pouta.csc.fi/OPUS-SETIMES/v2/moses/en-sq.txt.zip",
}


def head(url: str) -> tuple:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "albcourse/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.status, int(resp.headers.get("content-length", 0))


def main() -> None:
    for name, url in SOURCES.items():
        try:
            status, size = head(url)
            mb = size / 1e6
            flag = "TOO BIG" if mb > 400 else "ok"
            print(f"{name:<15}{status}  {mb:9.1f} MB  {flag}")
        except Exception as exc:  # noqa: BLE001 - report, do not crash the sweep
            print(f"{name:<15}ERR  {exc}")


if __name__ == "__main__":
    main()
