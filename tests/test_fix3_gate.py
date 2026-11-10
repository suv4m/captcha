import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.risk import get_required_features
from backend.app.store import store

@pytest.fixture
def client():
    return TestClient(app)

def test_session_needs_update_and_switch_compatibility(client):
    """
    Gate: Show a visual challenge, tick vision, and the new challenge is neither visual nor drag.
    Switch afterwards and the result is still compatible.
    Repeat for hearing (never audio), motor (never drag) and cognitive (never level 3).
    """
    def req_feats(idx=0):
        req = get_required_features("min")
        f = {k: 0.0 for k in req}
        if req:
            f[req[0]] = float(idx * 100 + 50)
        return f

    res = client.post("/api/session", json={
        "site_key": "test_site",
        "features": req_feats(1),
        "access_needs": [],
        "breach_cost": 50.0
    })
    assert res.status_code == 200
    sess_data = res.json()
    assert sess_data["action"] == "challenge"
    sid = sess_data["session_id"]
    orig_cid = sess_data["challenge"]["challenge_id"]
    orig_type = sess_data["challenge"]["type"]
    assert orig_type in ["visual", "drag"], f"Expected visual/drag, got {orig_type}"

    n_res = client.post("/api/session/needs", json={
        "session_id": sid,
        "access_needs": ["vision"]
    })
    assert n_res.status_code == 200, f"Expected 200 from /api/session/needs, got {n_res.status_code}"
    n_data = n_res.json()
    ch1 = n_data["challenge"]
    cid1 = ch1["challenge_id"]
    type1 = ch1["type"]
    assert type1 not in ["visual", "drag"], f"Vision need got incompatible type {type1}"
    assert cid1 != orig_cid, "Challenge ID must be updated"

    assert store.get_challenge(orig_cid) is None, "Previous challenge secret must be deleted"

    sw_res = client.post("/api/challenge/switch", json={"session_id": sid})
    assert sw_res.status_code == 200
    sw_data = sw_res.json()
    type_sw = sw_data["challenge"]["type"]
    assert type_sw not in ["visual", "drag"], f"Switched challenge for vision need got incompatible {type_sw}"
    assert sw_data["swap_count"] == 1, "Switch must count as 1 swap (needs update did not count as swap)"

    res_h = client.post("/api/session", json={
        "site_key": "test_site",
        "features": req_feats(2),
        "access_needs": [],
        "breach_cost": 50.0
    })
    sid_h = res_h.json()["session_id"]
    n_res_h = client.post("/api/session/needs", json={
        "session_id": sid_h,
        "access_needs": ["hearing"]
    })
    assert n_res_h.status_code == 200
    type_h = n_res_h.json()["challenge"]["type"]
    assert type_h != "audio", f"Hearing need got audio challenge: {type_h}"

    sw_h = client.post("/api/challenge/switch", json={"session_id": sid_h})
    assert sw_h.status_code == 200
    assert sw_h.json()["challenge"]["type"] != "audio", "Switched challenge for hearing got audio!"

    res_m = client.post("/api/session", json={
        "site_key": "test_site",
        "features": req_feats(3),
        "access_needs": [],
        "breach_cost": 50.0
    })
    sid_m = res_m.json()["session_id"]
    n_res_m = client.post("/api/session/needs", json={
        "session_id": sid_m,
        "access_needs": ["motor"]
    })
    assert n_res_m.status_code == 200
    type_m = n_res_m.json()["challenge"]["type"]
    assert type_m != "drag", f"Motor need got drag challenge: {type_m}"

    sw_m = client.post("/api/challenge/switch", json={"session_id": sid_m})
    assert sw_m.status_code == 200
    assert sw_m.json()["challenge"]["type"] != "drag", "Switched challenge for motor got drag!"

    res_c = client.post("/api/session", json={
        "site_key": "test_site",
        "features": req_feats(4),
        "access_needs": [],
        "breach_cost": 50.0
    })
    sid_c = res_c.json()["session_id"]
    n_res_c = client.post("/api/session/needs", json={
        "session_id": sid_c,
        "access_needs": ["cognitive"]
    })
    assert n_res_c.status_code == 200
    lvl_c = n_res_c.json()["challenge"]["level"]
    assert lvl_c < 3, f"Cognitive need got level 3 challenge: level {lvl_c}"

    sw_c = client.post("/api/challenge/switch", json={"session_id": sid_c})
    assert sw_c.status_code == 200
    assert sw_c.json()["challenge"]["level"] < 3, "Switched challenge for cognitive got level 3!"
