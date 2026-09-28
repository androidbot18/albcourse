#!/usr/bin/env python3
"""End-to-end check of the live GitHub Pages app.

The Node suites proved the scheduler, store and views in isolation. They
could not prove the wiring: that the page boots, fetches real data over the
network, renders a card, grades it, and persists progress to localStorage.

Run with:  python3 tools/e2e_live.py
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

FIREFOX = "/home/ubuntu/.cache/ms-playwright/firefox-1509/firefox/firefox"
URL = "https://androidbot18.github.io/albcourse/app/"
STORAGE_KEY = "albcourse.progress.v1"

failures = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)
    return cond


def main():
    console_errors = []

    with sync_playwright() as p:
        browser = p.firefox.launch(
            executable_path=FIREFOX if os.path.exists(FIREFOX) else None)
        page = browser.new_page()
        page.on("console",
                lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append("PAGEERROR: " + str(e)))

        page.goto(URL, wait_until="networkidle")
        page.wait_for_selector(".level-chip", timeout=30000)

        chips = page.locator(".level-chip").count()
        check(chips == 184, "level map renders all 184 levels (got %d)" % chips)
        head = page.inner_text("#view")
        check("loading" not in head.lower(), "boot did not leave the loading placeholder")

        # open a level -> family lesson view
        page.locator(".level-chip").first.click()
        page.wait_for_timeout(1500)
        lesson = page.inner_text("#view")
        check("loading" not in lesson.lower(), "level view resolved (not stuck loading)")
        check(len(lesson.strip()) > 40, "level view shows content")
        sq_words = page.locator(".word .sq").count()
        check(sq_words > 0, "level view lists Albanian words (got %d)" % sq_words)
        pos_texts = [t.strip() for t in
                     page.locator(".word .pos").all_inner_texts() if t.strip()]
        dupes = [t for t in pos_texts if len(set(x.strip() for x in t.split(","))) !=
                 len([x for x in t.split(",") if x.strip()])]
        check(not dupes, "no card repeats a POS label (e.g. %s)" % dupes[:3])

        # review session
        page.click("[data-view=study]")
        page.wait_for_timeout(1500)
        review = page.inner_text("#view")
        check(len(review.strip()) > 15, "review view rendered")

        # The answer is hidden until the learner asks for it, so the
        # grading buttons only exist after this click. Skipping it is what
        # made an earlier run of this test report a false failure.
        revealed = False
        for sel in (".reveal", "button.reveal", "[data-action=reveal]"):
            btn = page.locator(sel).first
            if btn.count() and btn.is_visible():
                btn.click()
                revealed = True
                break
        check(revealed, "a 'Show answer' control was present and clickable")
        page.wait_for_timeout(800)
        check(page.locator(".answer").count() > 0, "revealing showed the answer")

        graded = False
        for sel in (".grades button", "button.grade", "button[data-grade]"):
            btn = page.locator(sel).first
            if btn.count() and btn.is_visible():
                btn.click()
                graded = True
                break
        check(graded, "a grading button was present and clickable")

        page.wait_for_timeout(1200)
        raw = page.evaluate("localStorage.getItem('%s')" % STORAGE_KEY)
        check(raw is not None, "progress written to localStorage")
        if raw:
            data = json.loads(raw)
            started = len(data.get("items") or {})  # schema key is "items"
            check(started > 0, "localStorage records started cards (got %d)" % started)
            check(data.get("version") is not None, "stored payload is versioned")

        page.click("[data-view=stats]")
        page.wait_for_timeout(800)
        check(len(page.inner_text("#view").strip()) > 10, "progress view rendered")

        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1500)
        raw2 = page.evaluate("localStorage.getItem('%s')" % STORAGE_KEY)
        check(raw2 == raw, "progress survived a page reload")

        check(not console_errors,
              "no console errors (got %d: %s)" % (len(console_errors),
                                                  console_errors[:3]))
        browser.close()

    print()
    if failures:
        print("E2E FAILURES (%d):" % len(failures))
        for f in failures:
            print("  x %s" % f)
        return 1
    print("E2E PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
