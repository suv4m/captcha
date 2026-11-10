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


@pytest.fixture
def client():
    return TestClient(app)


def test_p0_live_behaviour(client):
    """
    Gate Fix 8:
    /api/session: implement P0 (fixed vis2, no scoring, 0 bytes).
    """
    res = client.post("/api/session", json={
        "site_key": "test_site",
        "features": {},
        "access_needs": [],
        "policy": "P0"
    })
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["action"] == "challenge"
    assert data["challenge"]["type"] == "visual"
    assert data["challenge"]["level"] == 2
    assert data["trace"]["policy"] == "P0"
    assert data["trace"]["data_sent_bytes"] == 0
    assert data["trace"]["chosen_id"] == "vis2"


def test_simulate_timing_under_one_second(client):
    """
    Gate Fix 8:
    /api/lab/simulate: cache loaded arrays and vectorise simulation.
    Target under 1s for 20 runs.
    """
    t0 = time.perf_counter()
    res = client.get("/api/lab/simulate?policy=P3&breach_cost=2.0&runs=20")
    t1 = time.perf_counter()
    elapsed = t1 - t0

    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "human_pass_rate" in data
    assert "bot_pass_rate" in data
    assert "mean_human_time_s" in data
    assert elapsed < 1.0, f"Simulation took {elapsed:.3f}s, expected under 1.0s!"


def test_cors_no_allow_credentials_with_wildcard(client):
    """
    Gate Fix 8:
    CORS: remove allow_credentials=True when allow_origins=['*'].
    """
    res = client.options("/api/health", headers={
        "Origin": "http://evil.com",
        "Access-Control-Request-Method": "GET"
    })
    # If credentials are not allowed, header is absent or 'false'
    cred_header = res.headers.get("access-control-allow-credentials")
    assert cred_header != "true", f"access-control-allow-credentials must not be 'true' with wildcard origins! Got: {cred_header}"


def test_site_key_validation(client):
    """
    Gate Fix 8:
    Validate site_key against a configured list.
    """
    res = client.post("/api/session", json={
        "site_key": "unregistered_bogus_key",
        "features": {},
        "access_needs": []
    })
    assert res.status_code == 400
    assert "site_key" in res.json().get("detail", "").lower()


def test_run_py_fails_loudly_on_training_error(monkeypatch):
    """
    Gate Fix 8:
    run.py catches only a missing ml.train module. Any other error fails loudly.
    """
    import run

    # 1. Non-ImportError in training must raise loudly
    def mock_train_broken():
        raise RuntimeError("Fatal hardware/dataset error")

    monkeypatch.setattr("ml.train.train_all", mock_train_broken)
    with pytest.raises(RuntimeError, match="Fatal hardware/dataset error"):
        run.main_train_step(force=True)
