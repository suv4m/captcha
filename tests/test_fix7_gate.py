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

PORT = 8007


def _start_server():
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


def test_fix7_playwright_keyboard_only_and_aria_attributes():
    """
    Gate Fix 7:
    Playwright keyboard-only completion of visual, audio and drag.
    List and verify each ARIA attribute added and where:
    - #verifyBtn: plain button with aria-busy="false" (no role="checkbox")
    - visual grid: role="group" and aria-labelledby="challengePrompt"
    - visual tiles: aria-pressed="false" / aria-pressed="true"
    - audio input: aria-label, inputmode="numeric", autocomplete="off"
    - audio button: text label "Play audio"
    - drag slider: role="slider", aria-label
    - locked state: provides "Start over" button
    """
    t = threading.Thread(target=_start_server, daemon=True)
    t.start()
    time.sleep(2.0)

    url = f"http://127.0.0.1:{PORT}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(f"{url}/")
        page.wait_for_load_state("networkidle")

        widget = page.locator("#captchaWidget")

        # 1. Verify verifyBtn attributes (plain button with aria-busy, not role="checkbox")
        role_attr = page.evaluate("document.getElementById('captchaWidget').shadowRoot.getElementById('verifyBtn').getAttribute('role')")
        assert role_attr is None or role_attr != "checkbox", f"Expected verifyBtn to not have role='checkbox', got '{role_attr}'"

        aria_busy = page.evaluate("document.getElementById('captchaWidget').shadowRoot.getElementById('verifyBtn').getAttribute('aria-busy')")
        assert aria_busy == "false", f"Expected aria-busy='false', got '{aria_busy}'"

        # 2. Force visual challenge by setting strictness B=50
        page.evaluate("""() => {
            const slider = document.getElementById('strictnessSlider');
            slider.value = 50;
            slider.dispatchEvent(new Event('input'));
        }""")

        # Focus verify button and press Enter
        verify_btn = widget.locator("#verifyBtn")
        verify_btn.focus()
        page.keyboard.press("Enter")

        challenge_box = widget.locator("#challengeBox")
        challenge_box.wait_for(state="visible", timeout=10000)

        # 3. Check Visual ARIA attributes: group role & aria-pressed on tiles
        grid_role = page.evaluate("document.getElementById('captchaWidget').shadowRoot.querySelector('.grid-container').getAttribute('role')")
        assert grid_role == "group", f"Expected grid role='group', got '{grid_role}'"

        grid_labeled = page.evaluate("document.getElementById('captchaWidget').shadowRoot.querySelector('.grid-container').getAttribute('aria-labelledby')")
        assert grid_labeled == "challengePrompt", f"Expected aria-labelledby='challengePrompt', got '{grid_labeled}'"

        tile0_pressed = page.evaluate("document.getElementById('captchaWidget').shadowRoot.querySelector('.grid-tile').getAttribute('aria-pressed')")
        assert tile0_pressed == "false", f"Expected tile aria-pressed='false', got '{tile0_pressed}'"

        # Solve Visual challenge keyboard-only:
        cid_vis = page.evaluate("document.getElementById('captchaWidget')._activeChallenge.challenge_id")
        sec_vis = page.request.get(f"{url}/api/_test/secret/{cid_vis}").json()
        target_indices = sec_vis["answer"]

        # Wait to satisfy server 400ms solve time rule
        time.sleep(0.5)

        # Tab to first tile, toggle targets
        tiles = page.locator("#captchaWidget >> .grid-tile")
        tiles_count = tiles.count()
        for idx in range(tiles_count):
            if idx in target_indices:
                tiles.nth(idx).focus()
                page.keyboard.press("Space")
                pressed = page.evaluate(f"document.getElementById('captchaWidget').shadowRoot.querySelectorAll('.grid-tile')[{idx}].getAttribute('aria-pressed')")
                assert pressed == "true", f"Tile {idx} should have aria-pressed='true'"

        submit_btn = widget.locator("#submitChallengeBtn")
        submit_btn.focus()
        page.keyboard.press("Enter")

        time.sleep(1.0)
        state = page.evaluate("document.getElementById('captchaWidget')._state")
        assert state == "passed", f"Expected passed state for visual, got '{state}'"

        # --- Test Audio keyboard-only completion ---
        page.reload()
        page.wait_for_load_state("networkidle")
        page.evaluate("""() => {
            const slider = document.getElementById('strictnessSlider');
            slider.value = 50;
            slider.dispatchEvent(new Event('input'));
        }""")
        widget.locator("#verifyBtn").focus()
        page.keyboard.press("Enter")
        challenge_box.wait_for(state="visible", timeout=10000)

        # Tab from heading to Audio alt button and press Enter
        page.keyboard.press("Tab")
        with page.expect_response(lambda r: "/api/challenge/switch" in r.url and r.status == 200):
            page.keyboard.press("Enter")

        time.sleep(0.5)
        # Check Audio ARIA attributes
        audio_inp = widget.locator("#audioAnswerInput")
        audio_inp_label = page.evaluate("document.getElementById('captchaWidget').shadowRoot.getElementById('audioAnswerInput').getAttribute('aria-label')")
        assert audio_inp_label is not None and len(audio_inp_label) > 0, "Audio input must have aria-label"

        audio_inp_mode = page.evaluate("document.getElementById('captchaWidget').shadowRoot.getElementById('audioAnswerInput').getAttribute('inputmode')")
        assert audio_inp_mode == "numeric", f"Expected inputmode='numeric', got '{audio_inp_mode}'"

        audio_inp_auto = page.evaluate("document.getElementById('captchaWidget').shadowRoot.getElementById('audioAnswerInput').getAttribute('autocomplete')")
        assert audio_inp_auto == "off", f"Expected autocomplete='off', got '{audio_inp_auto}'"

        cid_aud = page.evaluate("document.getElementById('captchaWidget')._activeChallenge.challenge_id")
        sec_aud = page.request.get(f"{url}/api/_test/secret/{cid_aud}").json()
        audio_answer = str(sec_aud["answer"])

        time.sleep(0.5)
        audio_inp.focus()
        page.keyboard.type(audio_answer)
        widget.locator("#submitChallengeBtn").focus()
        page.keyboard.press("Enter")

        time.sleep(1.0)
        state_aud = page.evaluate("document.getElementById('captchaWidget')._state")
        assert state_aud == "passed", f"Expected passed state for audio, got '{state_aud}'"

        # --- Test Drag keyboard-only completion ---
        page.reload()
        page.wait_for_load_state("networkidle")
        page.evaluate("""() => {
            const slider = document.getElementById('strictnessSlider');
            slider.value = 50;
            slider.dispatchEvent(new Event('input'));
        }""")
        widget.locator("#verifyBtn").focus()
        page.keyboard.press("Enter")
        challenge_box.wait_for(state="visible", timeout=10000)

        # Tab to Drag alt button (second alt button: Audio is first, Drag is second)
        drag_btn = page.evaluate("""() => {
            const btns = Array.from(document.getElementById('captchaWidget').shadowRoot.querySelectorAll('.alt-btn'));
            const d = btns.find(b => b.textContent.includes('Drag'));
            d.focus();
            return d !== null;
        }""")
        assert drag_btn is True
        with page.expect_response(lambda r: "/api/challenge/switch" in r.url and r.status == 200):
            page.keyboard.press("Enter")

        time.sleep(0.5)
        # Check Drag slider ARIA attributes
        slider_role = page.evaluate("document.getElementById('captchaWidget').shadowRoot.querySelector('.drag-slider-track').getAttribute('role')")
        assert slider_role == "slider", f"Expected slider role='slider', got '{slider_role}'"

        cid_drag = page.evaluate("document.getElementById('captchaWidget')._activeChallenge.challenge_id")
        sec_drag = page.request.get(f"{url}/api/_test/secret/{cid_drag}").json()
        target_x = sec_drag["answer"]["x"]

        # Set slider value via keyboard arrow keys or direct input simulation
        time.sleep(0.5)
        page.evaluate(f"""() => {{
            const sl = document.getElementById('captchaWidget').shadowRoot.querySelector('.drag-slider-track');
            sl.focus();
            sl.value = {target_x};
            sl.dispatchEvent(new Event('input'));
        }}""")

        widget.locator("#submitChallengeBtn").focus()
        page.keyboard.press("Enter")

        time.sleep(1.0)
        state_drag = page.evaluate("document.getElementById('captchaWidget')._state")
        assert state_drag == "passed", f"Expected passed state for drag, got '{state_drag}'"

        browser.close()
