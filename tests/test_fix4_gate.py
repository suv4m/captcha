import os
import sys
import time
import threading
from pathlib import Path
import uvicorn
import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ["CAPTCHA_TEST_MODE"] = "1"
from backend.app.main import app
from backend.app.risk import get_required_features

PORT = 8005


def _start_server():
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


@pytest.fixture
def client():
    return TestClient(app)


def test_switch_target_type_endpoint(client):
    """Test /api/challenge/switch with optional target_type."""
    req_feats = {k: 0.0 for k in get_required_features("min")}
    res = client.post("/api/session", json={
        "site_key": "test_site",
        "features": req_feats,
        "access_needs": [],
        "breach_cost": 50.0
    })
    assert res.status_code == 200
    sid = res.json()["session_id"]
    orig_type = res.json()["challenge"]["type"]

    # Target audio specifically
    sw_res = client.post("/api/challenge/switch", json={
        "session_id": sid,
        "target_type": "audio"
    })
    assert sw_res.status_code == 200
    data = sw_res.json()
    assert data["challenge"]["type"] == "audio", f"Expected target_type 'audio', got {data['challenge']['type']}"

    # Target drag specifically
    sw_res2 = client.post("/api/challenge/switch", json={
        "session_id": sid,
        "target_type": "drag"
    })
    assert sw_res2.status_code == 200
    data2 = sw_res2.json()
    assert data2["challenge"]["type"] == "drag", f"Expected target_type 'drag', got {data2['challenge']['type']}"


def test_keyboard_only_navigation_and_screen_reader_announcements():
    """
    Playwright Gate:
    Keyboard only: reach the alternative buttons with Tab, switch to audio, solve it.
    A screen-reader-style check shows the focus target and the live-region text after each render.
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

        # Set strictness high (B=50) to force a visual challenge
        page.evaluate("""() => {
            const slider = document.getElementById('strictnessSlider');
            slider.value = 50;
            slider.dispatchEvent(new Event('input'));
        }""")

        widget = page.locator("#captchaWidget")

        # 1. Start interaction via keyboard: Focus verify button and press Enter
        verify_btn = widget.locator("#verifyBtn")
        verify_btn.focus()
        page.keyboard.press("Enter")

        # Wait for challenge to show
        challenge_box = widget.locator("#challengeBox")
        challenge_box.wait_for(state="visible", timeout=10000)

        # 2. Check focus target and aria-live region
        # Heading must have tabindex="-1" and be focused
        focused_tag = page.evaluate("document.getElementById('captchaWidget').shadowRoot.activeElement.id")
        assert focused_tag == "challengePrompt", f"Expected challengePrompt focused, got '{focused_tag}'"

        live_text = page.evaluate("document.getElementById('captchaWidget').shadowRoot.getElementById('srStatus').textContent")
        assert "Press Tab for an audio alternative" in live_text, f"Unexpected live-region text: '{live_text}'"

        # 3. Press Tab to reach the 'Audio' alternative button
        # First Tab goes from heading to first alternative button
        page.keyboard.press("Tab")
        focused_btn_text = page.evaluate("document.getElementById('captchaWidget').shadowRoot.activeElement.textContent")
        assert "Audio" in focused_btn_text, f"Expected Audio alternative button focused, got '{focused_btn_text}'"

        # Press Enter on Audio alternative button
        with page.expect_response(lambda r: "/api/challenge/switch" in r.url and r.status == 200):
            page.keyboard.press("Enter")

        time.sleep(0.5)

        # 4. Verify switched to Audio and live-region announced
        ctype = page.evaluate("document.getElementById('captchaWidget')._activeChallenge.type")
        assert ctype == "audio", f"Expected audio challenge, got {ctype}"

        live_text_audio = page.evaluate("document.getElementById('captchaWidget').shadowRoot.getElementById('srStatus').textContent")
        assert "Audio challenge" in live_text_audio, f"Expected Audio announcement, got '{live_text_audio}'"

        # 5. Solve via keyboard only
        # Fetch secret from test hook
        cid = page.evaluate("document.getElementById('captchaWidget')._activeChallenge.challenge_id")
        sec_res = page.request.get(f"{url}/api/_test/secret/{cid}")
        assert sec_res.status == 200
        answer_digits = str(sec_res.json()["answer"])

        # Tab to audio input
        audio_input = widget.locator("#audioAnswerInput")
        audio_input.focus()
        page.keyboard.type(answer_digits)

        # Tab to Verify button and press Enter
        submit_btn = widget.locator("#submitChallengeBtn")
        submit_btn.focus()
        page.keyboard.press("Enter")

        time.sleep(1.0)
        state = page.evaluate("document.getElementById('captchaWidget')._state")
        assert state == "passed", f"Expected passed state, got '{state}'"

        browser.close()
