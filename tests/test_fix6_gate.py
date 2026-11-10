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


def test_challenge_reuse_after_success_rejected_409(client):
    """
    Gate Fix 6:
    On success: delete the challenge, set session.solved = true, issue exactly one token.
    A later verify returns 409.
    """
    feats = {k: 0.0 for k in get_required_features("min")}
    res = client.post("/api/session", json={
        "site_key": "test_site",
        "features": feats,
        "access_needs": [],
        "breach_cost": 100.0
    })
    assert res.status_code == 200
    sid = res.json()["session_id"]
    cid = res.json()["challenge"]["challenge_id"]

    # Fetch answer
    sec = client.get(f"/api/_test/secret/{cid}").json()
    answer = sec["answer"]

    # Solve successfully
    time.sleep(0.42)
    v1 = client.post("/api/challenge/verify", json={
        "session_id": sid,
        "challenge_id": cid,
        "answer": answer,
        "interaction": {}
    })
    assert v1.status_code == 200
    assert v1.json()["ok"] is True
    token1 = v1.json()["token"]
    assert token1 is not None

    # Re-verify attempt with same challenge_id MUST return 409 Conflict
    v2 = client.post("/api/challenge/verify", json={
        "session_id": sid,
        "challenge_id": cid,
        "answer": answer,
        "interaction": {}
    })
    assert v2.status_code == 409, f"Expected 409 for re-verify after success, got {v2.status_code}"


def test_preswap_challenge_id_rejected_400(client):
    """
    Gate Fix 6:
    A pre-swap challenge id is rejected with 400.
    Accept only session.current_challenge_id.
    """
    feats = {k: 0.0 for k in get_required_features("min")}
    res = client.post("/api/session", json={
        "site_key": "test_site",
        "features": feats,
        "access_needs": [],
        "breach_cost": 100.0
    })
    sid = res.json()["session_id"]
    cid_orig = res.json()["challenge"]["challenge_id"]

    # Fetch secret of original challenge before swap
    sec_orig = client.get(f"/api/_test/secret/{cid_orig}").json()
    answer_orig = sec_orig["answer"]

    # Swap challenge
    sw = client.post("/api/challenge/switch", json={"session_id": sid})
    assert sw.status_code == 200
    cid_swapped = sw.json()["challenge"]["challenge_id"]
    assert cid_swapped != cid_orig

    # Attempt to verify with pre-swap challenge id cid_orig
    time.sleep(0.42)
    v = client.post("/api/challenge/verify", json={
        "session_id": sid,
        "challenge_id": cid_orig,
        "answer": answer_orig,
        "interaction": {}
    })
    assert v.status_code == 400, f"Expected 400 for pre-swap challenge id, got {v.status_code}"


def test_session_yields_at_most_one_token(client):
    """
    Gate Fix 6:
    A session yields at most one token. Subsequent verification, swapping or needs update cannot mint another.
    """
    feats = {k: 0.0 for k in get_required_features("min")}
    res = client.post("/api/session", json={
        "site_key": "test_site",
        "features": feats,
        "access_needs": [],
        "breach_cost": 100.0
    })
    sid = res.json()["session_id"]
    cid = res.json()["challenge"]["challenge_id"]

    sec = client.get(f"/api/_test/secret/{cid}").json()
    answer = sec["answer"]

    time.sleep(0.42)
    v1 = client.post("/api/challenge/verify", json={
        "session_id": sid,
        "challenge_id": cid,
        "answer": answer,
        "interaction": {}
    })
    assert v1.status_code == 200
    assert v1.json()["ok"] is True
    token = v1.json()["token"]
    assert token is not None

    # Switch after solve fails
    sw = client.post("/api/challenge/switch", json={"session_id": sid})
    assert sw.status_code == 400

    # Needs update after solve fails
    nd = client.post("/api/session/needs", json={"session_id": sid, "access_needs": ["vision"]})
    assert nd.status_code == 400
