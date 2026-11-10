import os
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.decision import select_best_challenge
from backend.app.risk import get_required_features

@pytest.fixture
def client():
    return TestClient(app)

def test_test_hook_security_404_when_disabled():
    """Assert test hook GET /api/_test/secret/{id} returns 404 without CAPTCHA_TEST_MODE=1."""

    os.environ["CAPTCHA_TEST_MODE"] = "0"
    from backend.app import config
    config.CAPTCHA_TEST_MODE = False

    c = TestClient(app)
    res = c.get("/api/_test/secret/some_id")
    assert res.status_code == 404, "Test hook must return 404 when test mode is disabled!"

    config.CAPTCHA_TEST_MODE = True
    os.environ["CAPTCHA_TEST_MODE"] = "1"

def test_accessibility_constraint_30_sessions():
    """
    With vision declared, 30 sessions never produce visual or drag challenges.
    With vision and hearing declared, only PoW is produced and step-up note appears at high risk.
    """
    p_values = [0.05, 0.1, 0.2, 0.35, 0.55, 0.75, 0.95]

    for i in range(30):
        p = p_values[i % len(p_values)]
        B = 60.0 + (i * 4)
        dec = select_best_challenge(p, ["vision"], B=B)
        chosen_type = dec["chosen_type"]
        assert chosen_type not in ["visual", "drag"], (
            f"Accessibility violation: 'vision' declared but received {chosen_type} (id: {dec['chosen_id']})"
        )

    for i in range(15):
        p = 0.55 + (i * 0.03)
        B = 60.0
        dec = select_best_challenge(p, ["vision", "hearing"], B=B)
        chosen_type = dec["chosen_type"]
        assert chosen_type == "pow", (
            f"Expected only PoW for vision+hearing, got {chosen_type}"
        )

        assert dec["step_up_suggested"] is True, "Step-up suggested note must appear at high risk with weak accessible set!"

def test_keyboard_assistive_flow(client):
    """A keyboard-assistive run completes a challenge using only keyboard events."""

    keyboard_features = {k: 0.0 for k in get_required_features("min")}

    res = client.post("/api/session", json={
        "site_key": "test_keyboard",
        "features": keyboard_features,
        "access_needs": ["motor"],
        "breach_cost": 60.0
    })
    assert res.status_code == 200
    sess = res.json()
    sid = sess["session_id"]

    if sess["action"] == "challenge":
        ch = sess["challenge"]
        cid = ch["challenge_id"]

        sec_res = client.get(f"/api/_test/secret/{cid}")
        assert sec_res.status_code == 200
        answer = sec_res.json()["answer"]

        import time
        time.sleep(0.42)
        v_res = client.post("/api/challenge/verify", json={
            "session_id": sid,
            "challenge_id": cid,
            "answer": answer,
            "interaction": {}
        })
        assert v_res.status_code == 200
        assert v_res.json()["ok"] is True
        token = v_res.json()["token"]

        sv = client.post("/api/siteverify", json={"token": token})
        assert sv.status_code == 200
        assert sv.json()["success"] is True

