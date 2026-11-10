import os
import sys
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ["CAPTCHA_TEST_MODE"] = "1"
from backend.app.main import app
from backend.app.risk import get_required_features


@pytest.fixture
def client():
    return TestClient(app)


def test_server_measured_solve_time_visual_fails_pow_passes(client):
    """
    Gate Fix 5:
    1. A correct visual answer submitted immediately after issue fails as too fast (server-measured < 400ms).
       Even if client attempts to forge duration_ms: 5000 in interaction dict.
    2. A pow1 solution submitted quickly passes (400ms rule never applies to PoW).
    """
    req = get_required_features("min")
    feats = {k: 0.0 for k in req}
    if req:
        feats[req[0]] = 543.21

    # --- Test 1: Immediate visual answer fails ---
    res_vis = client.post("/api/session", json={
        "site_key": "test_site",
        "features": feats,
        "access_needs": ["motor"],
        "breach_cost": 100.0  # forces visual (drag is incompatible with motor)
    })
    assert res_vis.status_code == 200
    vis_data = res_vis.json()
    assert vis_data["challenge"]["type"] == "visual"
    vis_sid = vis_data["session_id"]
    vis_cid = vis_data["challenge"]["challenge_id"]

    # Get correct answer via test hook
    sec_vis = client.get(f"/api/_test/secret/{vis_cid}").json()
    correct_vis_answer = sec_vis["answer"]

    # Submit immediately (< 100ms) with forged duration_ms claiming 5000ms
    v_res = client.post("/api/challenge/verify", json={
        "session_id": vis_sid,
        "challenge_id": vis_cid,
        "answer": correct_vis_answer,
        "interaction": {"duration_ms": 5000}  # forged client value must be ignored
    })
    assert v_res.status_code == 200
    v_json = v_res.json()
    assert v_json["ok"] is False, "Visual answer submitted immediately must fail as too fast!"
    assert "too fast" in v_json["error"].lower()

    # --- Test 2: Quick PoW solution passes ---
    # High-risk bot trace with vision+hearing needs selects pow
    feats_pow = {k: 0.0 for k in req}
    if req:
        feats_pow[req[0]] = 999.0

    res_pow = client.post("/api/session", json={
        "site_key": "test_site",
        "features": feats_pow,
        "access_needs": ["vision", "hearing"],
        "breach_cost": 50.0
    })
    assert res_pow.status_code == 200
    pow_data = res_pow.json()
    assert pow_data["challenge"]["type"] == "pow"
    pow_sid = pow_data["session_id"]
    pow_cid = pow_data["challenge"]["challenge_id"]

    sec_pow = client.get(f"/api/_test/secret/{pow_cid}").json()
    pow_answer = sec_pow["answer"]

    # Submit immediately (< 100ms)
    v_pow = client.post("/api/challenge/verify", json={
        "session_id": pow_sid,
        "challenge_id": pow_cid,
        "answer": pow_answer,
        "interaction": {}
    })
    assert v_pow.status_code == 200
    v_pow_json = v_pow.json()
    assert v_pow_json["ok"] is True, f"Quick pow1 solution should pass! Got: {v_pow_json}"
    assert v_pow_json["token"] is not None
