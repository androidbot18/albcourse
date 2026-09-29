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

        # A borrowed sibling-sense example must be labelled, so the sentence
        # is never read as illustrating the headline gloss. The queue is walked
        # until a labelled card appears, because the first card may not be one.
        # Order matters: reveal FIRST, then look for the label, then grade.
        # Checking for .ex-note before revealing looks at the next card while
        # its answer is still hidden, so the walk never sees a label.
        seen_borrowed = False
        for _ in range(40):
            reveal2 = page.query_selector("button.reveal")
            if reveal2:
                reveal2.click()
                page.wait_for_timeout(200)
            note = page.query_selector(".ex-note")
            if note is not None and note.inner_text().strip():
                seen_borrowed = True
                print("      borrowed label: %s" % note.inner_text().strip()[:70])
                break
            # The grade buttons are .grade.grade-<cls> inside .grades, not
            # descendants - ".grade button" matches nothing.
            nxt = page.query_selector(".grades .grade")
            if nxt is None:
                break
            nxt.click()
            page.wait_for_timeout(250)
        ok(seen_borrowed, "a borrowed sibling-sense example shows its sense label")

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
