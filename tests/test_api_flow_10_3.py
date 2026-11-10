import json
import time
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.store import store
from backend.app.risk import get_required_features


@pytest.fixture
def client():
    return TestClient(app)


def _get_dummy_features():
    import random
    req = get_required_features("min")
    feats = {k: 0.0 for k in req}
    if req:
        feats[req[0]] = round(random.uniform(500, 5000), 1)
    return feats


def test_full_flow_all_four_types(client):
    """Run full session -> solve -> siteverify flow for each challenge type."""
    for ctype in ["visual", "audio", "drag", "pow"]:
        bot_features = _get_dummy_features()
        # We enforce type by setting access_needs appropriately or selecting
        if ctype == "visual":
            needs = []
            # high B + p triggers visual/drag
        elif ctype == "audio":
            needs = ["vision"]
        elif ctype == "drag":
            needs = ["hearing"]
        elif ctype == "pow":
            needs = ["vision", "hearing"]

        # 1. Create session
        res = client.post("/api/session", json={
            "site_key": "test_site",
            "features": bot_features,
            "access_needs": needs,
            "breach_cost": 150.0
        })
        assert res.status_code == 200
        sess_data = res.json()
        assert sess_data["action"] == "challenge"
        sid = sess_data["session_id"]
        ch = sess_data["challenge"]
        cid = ch["challenge_id"]

        # Verify no secrets in response
        res_text = res.text
        ch_store = store.get_challenge(cid)
        sec = ch_store["secret"]

        if "digits" in sec:
            assert sec["digits"] not in res_text
        if "target_indices" in sec:
            # check that full list of indices is not directly exposed
            assert f'"target_indices":{json.dumps(sec["target_indices"])}' not in res_text
        if "hole_x" in sec:
            assert f'"hole_x":{sec["hole_x"]}' not in res_text

        # 2. Get answer from in-process store for test verification
        actual_type = ch_store["type"]
        if actual_type == "visual":
            answer = sec["target_indices"]
        elif actual_type == "audio":
            answer = sec["digits"]
        elif actual_type == "drag":
            answer = {"x": sec["hole_x"]}
        elif actual_type == "pow":
            import hashlib
            from backend.app.challenges import pow as pow_mod
            nonce = sec["nonce"]
            bits = sec["bits"]
            counter = 0
            while True:
                h = hashlib.sha256(f"{nonce}:{counter}".encode("utf-8")).digest()
                if pow_mod.count_leading_zero_bits(h) >= bits:
                    answer = {"counter": counter}
                    break
                counter += 1

        if actual_type in ["visual", "audio", "drag"]:
            time.sleep(0.42)

        # 3. Verify challenge (>400ms duration)
        v_res = client.post("/api/challenge/verify", json={
            "session_id": sid,
            "challenge_id": cid,
            "answer": answer,
            "interaction": {}
        })
        assert v_res.status_code == 200
        v_data = v_res.json()
        assert v_data["ok"] is True
        token = v_data["token"]
        assert token is not None

        # 4. Siteverify
        sv_res = client.post("/api/siteverify", json={"token": token})
        assert sv_res.status_code == 200
        sv_data = sv_res.json()
        assert sv_data["success"] is True
        assert sv_data["challenge_type"] == actual_type

        # Replay attempt fails
        replay_res = client.post("/api/siteverify", json={"token": token})
        assert replay_res.status_code == 200
        assert replay_res.json()["success"] is False


def test_400ms_anti_automation_rule(client):
    """Solves faster than 400 ms fail as automation (visual, audio, drag)."""
    res = client.post("/api/session", json={
        "site_key": "test_site",
        "features": _get_dummy_features(),
        "access_needs": [],
        "breach_cost": 100.0
    })
    sess_data = res.json()
    sid = sess_data["session_id"]
    cid = sess_data["challenge"]["challenge_id"]

    # Solve immediately without delay (< 400ms server elapsed)
    v_res = client.post("/api/challenge/verify", json={
        "session_id": sid,
        "challenge_id": cid,
        "answer": "any",
        "interaction": {}
    })
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["ok"] is False
    assert "too fast" in v_data["error"]
    assert v_data["attempts_left"] == 2


def test_attempts_and_lock_rule(client):
    """3 attempts per session; fresh challenge after failure; locked on 3rd fail."""
    res = client.post("/api/session", json={
        "site_key": "test_site",
        "features": _get_dummy_features(),
        "access_needs": [],
        "breach_cost": 100.0
    })
    sid = res.json()["session_id"]
    cid = res.json()["challenge"]["challenge_id"]

    # 1st fail (wait >400ms so failure reason is incorrect answer, not too fast)
    time.sleep(0.42)
    v1 = client.post("/api/challenge/verify", json={
        "session_id": sid, "challenge_id": cid, "answer": "wrong",
        "interaction": {}
    }).json()
    assert v1["ok"] is False
    assert v1["attempts_left"] == 2
    assert v1["locked"] is False
    new_cid = v1["new_challenge"]["challenge_id"]

    # 2nd fail
    time.sleep(0.42)
    v2 = client.post("/api/challenge/verify", json={
        "session_id": sid, "challenge_id": new_cid, "answer": "wrong_again",
        "interaction": {}
    }).json()
    assert v2["ok"] is False
    assert v2["attempts_left"] == 1
    assert v2["locked"] is False
    new_cid_2 = v2["new_challenge"]["challenge_id"]

    # 3rd fail -> Locked!
    time.sleep(0.42)
    v3 = client.post("/api/challenge/verify", json={
        "session_id": sid, "challenge_id": new_cid_2, "answer": "wrong_3rd",
        "interaction": {}
    }).json()
    assert v3["ok"] is False
    assert v3["attempts_left"] == 0
    assert v3["locked"] is True

    # 4th attempt on locked session returns error
    v4 = client.post("/api/challenge/verify", json={
        "session_id": sid, "challenge_id": new_cid_2, "answer": "whatever",
        "interaction": {"duration_ms": 600}
    }).json()
    assert v4["locked"] is True


def test_switch_endpoint_and_limit(client):
    """User escape switch allows at most 2 swaps and excludes current type."""
    res = client.post("/api/session", json={
        "site_key": "test_site",
        "features": _get_dummy_features(),
        "access_needs": [],
        "breach_cost": 100.0
    })
    sid = res.json()["session_id"]
    orig_type = res.json()["challenge"]["type"]

    # Swap 1
    sw1 = client.post("/api/challenge/switch", json={"session_id": sid})
    assert sw1.status_code == 200
    assert sw1.json()["swap_count"] == 1
    assert sw1.json()["challenge"]["type"] != orig_type
    type2 = sw1.json()["challenge"]["type"]

    # Swap 2
    sw2 = client.post("/api/challenge/switch", json={"session_id": sid})
    assert sw2.status_code == 200
    assert sw2.json()["swap_count"] == 2
    assert sw2.json()["challenge"]["type"] != type2

    # Swap 3 -> exceeds max 2 swaps
    sw3 = client.post("/api/challenge/switch", json={"session_id": sid})
    assert sw3.status_code == 400


def test_audio_endpoint_headers(client):
    """GET /api/challenge/{id}/audio returns audio/wav with Cache-Control: no-store."""
    res = client.post("/api/session", json={
        "site_key": "test_site",
        "features": _get_dummy_features(),
        "access_needs": ["vision"],
        "breach_cost": 120.0
    })
    sid = res.json()["session_id"]
    ch = res.json()["challenge"]
    cid = ch["challenge_id"]
    if ch.get("type") != "audio":
        sw = client.post("/api/challenge/switch", json={"session_id": sid, "target_type": "audio"})
        ch = sw.json()["challenge"]
        cid = ch["challenge_id"]

    audio_res = client.get(f"/api/challenge/{cid}/audio")
    assert audio_res.status_code == 200
    assert "audio/wav" in audio_res.headers.get("content-type", "")
    assert "no-store" in audio_res.headers.get("cache-control", "")
    assert len(audio_res.content) > 1000

