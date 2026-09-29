#!/usr/bin/env python3
"""Serve the repo briefly and check the study card in a real browser.

Run:  python3 tools/serve_check.py

Starts http.server in a thread, drives the page with Playwright/Firefox,
verifies a revealed review card renders BOTH halves of an example, then exits.
This is the check that matters: the Node suites proved logic, and twice now a
defect lived purely in the wiring between the data and the view.
"""
import json
import os
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

FIREFOX = "/home/ubuntu/.cache/ms-playwright/firefox-1509/firefox/firefox"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8767


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    os.chdir(ROOT)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Quiet)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(1)

    from playwright.sync_api import sync_playwright

    url = "http://127.0.0.1:%d/app/" % PORT

    fails = []

    def ok(cond, name, extra=""):
        line = ("  ok " if cond else "  x  ") + name
        if extra and not cond:
            line += "  [" + extra + "]"
        print(line)
        if not cond:
            fails.append(name)

    with sync_playwright() as p:
        browser = p.firefox.launch(executable_path=FIREFOX)
        page = browser.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1500)

        chips = page.query_selector_all(".level-chip")
        ok(len(chips) > 0, "the level map rendered chips",
           str(len(chips)) + " chips")

        # The review card lives behind the "Review" tab (data-view="study").
        # Opening a level shows the family lesson, which is a different view.
        page.click('[data-view="study"]')
        page.wait_for_timeout(800)

        reveal = page.query_selector("button.reveal")
        ok(reveal is not None, "the review tab offers a Show answer button")
        if reveal is None:
            print("      body: " + page.inner_text("body")[:300])
            browser.close()
            srv.shutdown()
            sys.exit(1)

        ok("ex-sq" not in page.content(),
           "no example box before the answer is revealed")

        reveal.click()
        page.wait_for_timeout(600)

        sq = page.query_selector(".card .ex-sq")
        en = page.query_selector(".card .ex-en")

        ok(sq is not None, "revealed card renders .ex-sq (Albanian sentence)")
        ok(en is not None, "revealed card renders .ex-en (English translation)")

        if sq is not None and en is not None:
            ok(sq.is_visible(), ".ex-sq is visible")
            ok(en.is_visible(), ".ex-en is visible")
            a = sq.inner_text().strip()
            b = en.inner_text().strip()
            ok(a != "", "the Albanian sentence has text", repr(a))
            ok(b != "", "the English translation has text", repr(b))
            ok(a != b, "the two halves are different strings",
               repr(a) + " vs " + repr(b))
            print("      shown: %s  /  %s" % (a, b))

        ok(not errors, "no console errors", "; ".join(errors[:3]))
        browser.close()

    srv.shutdown()
    print()
    if fails:
        print("FAILURES (%d): %s" % (len(fails), "; ".join(fails)))
        sys.exit(1)
    print("LOCAL BROWSER CHECK PASSED")


if __name__ == "__main__":
    main()
