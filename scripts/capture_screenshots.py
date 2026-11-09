import os
import sys
import time
import threading
from pathlib import Path
import uvicorn
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ["CAPTCHA_TEST_MODE"] = "1"
from backend.app.main import app

SCREENS_DIR = BASE_DIR / "docs" / "screens"


def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")


def capture_all():
    SCREENS_DIR.mkdir(parents=True, exist_ok=True)
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    time.sleep(2.5)

    base_url = "http://127.0.0.1:8002"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        configs = [
            ("1280_light", 1280, 800, "light"),
            ("1280_dark", 1280, 800, "dark"),
            ("375_light", 375, 750, "light"),
            ("375_dark", 375, 750, "dark"),
        ]

        for tag, width, height, scheme in configs:
            context = browser.new_context(
                viewport={"width": width, "height": height},
                color_scheme=scheme
            )
            page = context.new_page()

            # 1. Demo page
            page.goto(f"{base_url}/")
            page.wait_for_load_state("networkidle")
            time.sleep(0.5)
            demo_out = SCREENS_DIR / f"demo_{tag}.png"
            page.screenshot(path=str(demo_out), full_page=True)
            print(f"Captured: {demo_out}")

            # 2. Lab page
            page.goto(f"{base_url}/lab")
            page.wait_for_load_state("networkidle")
            time.sleep(1.0)
            lab_out = SCREENS_DIR / f"lab_{tag}.png"
            page.screenshot(path=str(lab_out), full_page=True)
            print(f"Captured: {lab_out}")

            context.close()

        browser.close()

    print(f"All 8 screenshots successfully captured in {SCREENS_DIR}")


if __name__ == "__main__":
    capture_all()

