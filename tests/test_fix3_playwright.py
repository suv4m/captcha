import os
import sys
import time
import threading
from pathlib import Path
import uvicorn
import pytest
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ["CAPTCHA_TEST_MODE"] = "1"
from backend.app.main import app

PORT = 8003

def _start_server():
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")

def test_fix3_playwright_gate():
    """
    Playwright Gate:
    Show a visual challenge, tick vision, and the new challenge is neither visual nor drag.
    Switch afterwards and the result is still compatible.
    Repeat for hearing (never audio), motor (never drag) and cognitive (never level 3).
    """
    t = threading.Thread(target=_start_server, daemon=True)
    t.start()
    time.sleep(2.0)

    url = f"http://127.0.0.1:{PORT}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        scenarios = [
            ("vision", lambda c, lvl: c not in ["visual", "drag"]),
            ("hearing", lambda c, lvl: c != "audio"),
            ("motor", lambda c, lvl: c != "drag"),
            ("cognitive", lambda c, lvl: lvl < 3),
        ]

        for need, check_fn in scenarios:
            context = browser.new_context()
            page = context.new_page()

            page.goto(f"{url}/")
            page.wait_for_load_state("networkidle")

            page.evaluate("""() => {
                const w = document.getElementById('captchaWidget');
                w.setAttribute('policy', 'P0');
                w.policy = 'P0';
            }""")

            widget = page.locator("#captchaWidget")
            verify_btn = widget.locator("#verifyBtn")
            verify_btn.click()

            challenge_box = widget.locator("#challengeBox")
            challenge_box.wait_for(state="visible", timeout=10000)

            a11y_toggle = widget.locator("#a11yToggle")
            a11y_toggle.click()

            cb = widget.locator(f".a11y-cb[value='{need}']")
            with page.expect_response(lambda r: "/api/session/needs" in r.url and r.status == 200):
                cb.check()

            page.evaluate("document.getElementById('captchaWidget')._stopPowWorker()")

            ctype = page.evaluate("document.getElementById('captchaWidget')._activeChallenge.type")
            lvl = page.evaluate("document.getElementById('captchaWidget')._activeChallenge.level")
            assert check_fn(ctype, lvl), f"Need '{need}' got incompatible replacement: type={ctype}, level={lvl}"

            switch_btn = widget.locator("#switchBtn")
            with page.expect_response(lambda r: "/api/challenge/switch" in r.url and r.status == 200):
                switch_btn.click()

            page.evaluate("document.getElementById('captchaWidget')._stopPowWorker()")

            ctype_sw = page.evaluate("document.getElementById('captchaWidget')._activeChallenge.type")
            lvl_sw = page.evaluate("document.getElementById('captchaWidget')._activeChallenge.level")
            assert check_fn(ctype_sw, lvl_sw), f"Need '{need}' after switch got incompatible: type={ctype_sw}, level={lvl_sw}"

            context.close()

        browser.close()
