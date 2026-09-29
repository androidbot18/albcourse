"""Poll GitHub Pages until the build for the merge commit finishes."""
import json
import subprocess
import sys
import time
import urllib.request

REPO = "androidbot18/albcourse"
URL = "https://androidbot18.github.io/albcourse/data/index.json"


def build_status():
    out = subprocess.run(
        ["gh", "api", "repos/%s/pages/builds/latest" % REPO, "--jq", ".status"],
        capture_output=True, text=True, timeout=60,
    )
    return out.stdout.strip() or out.stderr.strip()


def live_levels():
    req = urllib.request.Request(URL, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as fh:
        return len(json.load(fh))


for i in range(1, 16):
    st = build_status()
    try:
        n = live_levels()
    except Exception as exc:
        n = "err %s" % exc
    print("poll %2d: build=%-10s live levels=%s" % (i, st, n), flush=True)
    if st not in ("building", "queued") and n == 544:
        print("\nDEPLOYED: 544 levels live")
        sys.exit(0)
    time.sleep(20)

print("\nnot deployed yet; check again shortly")
sys.exit(1)
