# Drive the real page in a real browser and check the cognate line renders.
#
# The Node suite cannot see this: it stubs cognateLine to return null, so a
# broken or missing DOM element would pass every test. This class of defect
# has already shipped three times in this project (a blank review card, a
# duplicated POS label, a missing example half), each time invisible to the
# unit tests and obvious in the browser.
#
# Two bugs in the earlier version of this file, both worth remembering:
#
# 1. It scanned the first 60 chips by index and clicked each one. That cannot
#    work -- clicking a chip swaps the grid for the level view, so the second
#    click waits for a .level-chip that no longer exists.
# 2. It then selected the target chip with has_text="6". That is a substring
#    match, and level 5's chip contains "6w" (its word count), so it opened
#    the wrong level. The level number must be matched exactly, and has_text
#    needs a compiled pattern -- a plain "^6$" string is treated literally.
#
# So: read which level actually holds a cognate card from the shipped data,
# then open that one chip by its exact .lvl-num text.
import http.server
import json
import os
import re
import socketserver
import sys
import threading
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8731


def serve():
    os.chdir(ROOT)
    h = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), h)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def target_level():
    """The lowest level that contains a card with a cognate hook."""
    with open(os.path.join(ROOT, "data", "words.json"), encoding="utf-8") as fh:
        words = json.load(fh)["words"]
    hit = [w for w in words if w.get("cognate")]
    if not hit:
        return None, None
    first = min(hit, key=lambda w: w["level"])
    return first["level"], first["cognate"]


def main():
    httpd = serve()
    time.sleep(0.4)
    url = "http://127.0.0.1:%d/app/" % PORT
    try:
        urllib.request.urlopen(url, timeout=10).read()
    except Exception as e:
        print("FAIL  server did not serve the app: %s" % e)
        httpd.shutdown()
        return 1

    level_no, expect = target_level()
    if level_no is None:
        print("FAIL  no card in the shipped data carries a cognate hook")
        httpd.shutdown()
        return 1
    print("target level: %d (expected hook %r)" % (level_no, expect))

    from playwright.sync_api import sync_playwright

    fails = []
    with sync_playwright() as p:
        b = p.firefox.launch()
        pg = b.new_page()
        errors = []
        pg.on("console", lambda m: errors.append(m.text)
              if m.type == "error" else None)
        pg.goto(url, wait_until="networkidle")
        try:
            pg.wait_for_selector(".level-chip", timeout=20000)
        except Exception as e:
            fails.append("level grid never rendered: %s" % str(e)[:80])
            b.close()
            httpd.shutdown()
            for f in fails:
                print("  x %s" % f)
            return 1

        # Exact match on the .lvl-num span. has_text needs a compiled pattern;
        # a plain "^6$" string is treated as a literal and matches nothing.
        chip = pg.locator(".level-chip").filter(
            has=pg.locator(".lvl-num",
                           has_text=re.compile(r"^%s$" % level_no))).first
        chip.click()
        try:
            pg.wait_for_selector(".word", timeout=20000)
        except Exception as e:
            fails.append("level view never rendered: %s" % str(e)[:80])

        if not fails:
            joined = "\n".join(pg.locator(".word").all_inner_texts())
            if expect not in joined:
                fails.append("expected hook %r on the page, got: %r"
                              % (expect, joined[:200]))
            else:
                print("level %d renders its cognate: %r" % (level_no, expect))
            # Parentheses must balance: the extractor emits forms like
            # 'from Turkish sahi ("really, truly")'.
            for t in joined.split("\n"):
                if t.count("(") != t.count(")"):
                    fails.append("unbalanced parentheses in rendered text: %r"
                                  % t[:90])
        if errors:
            fails.append("console errors: %s" % errors[:3])
        b.close()
    httpd.shutdown()

    if fails:
        print("FAILURES (%d):" % len(fails))
        for f in fails:
            print("  x %s" % f)
        return 1
    print("COGNATE RENDER CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
