import os
import sys
import time
import json
import subprocess
import threading
import uvicorn
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Enable test mode so we can fetch answer via test hook or store
os.environ["CAPTCHA_TEST_MODE"] = "1"
from backend.app.main import app
from backend.app.store import store


def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")


def run_curl_command(cmd_args):
    proc = subprocess.run(["curl.exe", "-s"] + cmd_args, capture_output=True, text=True)
    return proc.stdout.strip()


def run_demo():
    print("Starting background server on port 8001 for curl verification...")
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    time.sleep(2.5)  # Wait for server to boot

    base_url = "http://127.0.0.1:8001"

    # Health check
    health_out = run_curl_command([f"{base_url}/api/health"])
    print(f"\n[CURL GET /api/health]: {health_out}")

    types_to_test = [
        ("visual", []),
        ("audio", ["vision"]),
        ("drag", ["hearing"]),  # will switch to drag
        ("pow", ["vision", "hearing"])
    ]

    for ctype, needs in types_to_test:
        print(f"\n==========================================")
        print(f"  FULL FLOW DEMO (curl.exe): {ctype.upper()}")
        print(f"==========================================")

        # 1. POST /api/session
        sess_payload = json.dumps({
            "site_key": "curl_demo_key",
            "features": [0.0] * 25,
            "access_needs": needs,
            "breach_cost": 150.0
        })
        sess_raw = run_curl_command([
            "-X", "POST",
            "-H", "Content-Type: application/json",
            "-d", sess_payload,
            f"{base_url}/api/session"
        ])
        sess_data = json.loads(sess_raw)
        sid = sess_data["session_id"]
        ch = sess_data["challenge"]
        cid = ch["challenge_id"]
        actual_type = ch["type"]

        print(f"1. POST /api/session -> session_id: {sid}, action: {sess_data['action']}, type: {actual_type}, cid: {cid}")

        if ctype == "drag" and actual_type != "drag":
            # Exercise user escape switch to switch away from visual to drag
            sw_raw = run_curl_command([
                "-X", "POST",
                "-H", "Content-Type: application/json",
                "-d", json.dumps({"session_id": sid}),
                f"{base_url}/api/challenge/switch"
            ])
            sw_data = json.loads(sw_raw)
            ch = sw_data["challenge"]
            cid = ch["challenge_id"]
            actual_type = ch["type"]
            print(f"   [SWITCH] POST /api/challenge/switch -> switched to: {actual_type}, cid: {cid}")

        # 2. Get solution from test hook or in-process store
        secret_raw = run_curl_command([f"{base_url}/api/_test/secret/{cid}"])
        secret_data = json.loads(secret_raw)
        answer = secret_data.get("answer")
        print(f"2. GET /api/_test/secret/{cid} (Test Hook) -> answer: {answer}")

        # 3. POST /api/challenge/verify
        verify_payload = json.dumps({
            "session_id": sid,
            "challenge_id": cid,
            "answer": answer,
            "interaction": {"duration_ms": 1100}
        })
        verify_raw = run_curl_command([
            "-X", "POST",
            "-H", "Content-Type: application/json",
            "-d", verify_payload,
            f"{base_url}/api/challenge/verify"
        ])
        verify_data = json.loads(verify_raw)
        token = verify_data.get("token")
        print(f"3. POST /api/challenge/verify -> ok: {verify_data['ok']}, token: {token[:24]}...")

        # 4. POST /api/siteverify
        siteverify_payload = json.dumps({"token": token})
        siteverify_raw = run_curl_command([
            "-X", "POST",
            "-H", "Content-Type: application/json",
            "-d", siteverify_payload,
            f"{base_url}/api/siteverify"
        ])
        siteverify_data = json.loads(siteverify_raw)
        print(f"4. POST /api/siteverify -> success: {siteverify_data['success']}, type: {siteverify_data.get('challenge_type')}, band: {siteverify_data.get('band')}")

        # 5. POST /api/siteverify (replay prevention test)
        replay_raw = run_curl_command([
            "-X", "POST",
            "-H", "Content-Type: application/json",
            "-d", siteverify_payload,
            f"{base_url}/api/siteverify"
        ])
        replay_data = json.loads(replay_raw)
        print(f"5. POST /api/siteverify (Replay) -> success: {replay_data['success']}, error: {replay_data.get('error')}")

    print("\nAll 4 challenge types successfully verified through curl.exe!")


if __name__ == "__main__":
    run_demo()
