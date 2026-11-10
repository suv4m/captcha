import json
import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ["CAPTCHA_TEST_MODE"] = "1"
from backend.app.main import app
from backend.app.config import ARTIFACTS_DIR
from backend.app.risk import get_required_features


@pytest.fixture
def client():
    return TestClient(app)


def test_metrics_json_reports_fix9_fields():
    """
    Gate Fix 9:
    metrics.json reports:
    - AUC with and without replay
    - replay guard's detection rate on duplicated vectors
    - autofill_desktop false-positive rate
    - seeds stay disjoint
    """
    metrics_path = ARTIFACTS_DIR / "metrics.json"
    assert metrics_path.exists(), "metrics.json must exist"

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    # 1. Seeds stay disjoint
    seeds = metrics.get("seeds", {})
    train_s = seeds.get("train")
    val_s = seeds.get("val")
    test_s = seeds.get("test")
    assert train_s is not None and val_s is not None and test_s is not None
    assert len({train_s, val_s, test_s}) == 3, f"Seeds must be disjoint: {seeds}"

    # 2. AUC with and without replay
    auc_comp = metrics.get("auc_with_and_without_replay", {})
    assert "full_with_replay" in auc_comp, "full_with_replay missing"
    assert "full_without_replay" in auc_comp, "full_without_replay missing"
    assert "min_with_replay" in auc_comp, "min_with_replay missing"
    assert "min_without_replay" in auc_comp, "min_without_replay missing"
    assert 0.5 <= auc_comp["full_without_replay"] <= 1.0
    assert 0.5 <= auc_comp["min_without_replay"] <= 1.0

    # 3. Replay guard detection rate on duplicated vectors
    rg = metrics.get("replay_guard", {})
    assert "detection_rate_on_duplicates" in rg, "detection_rate_on_duplicates missing"
    assert rg["detection_rate_on_duplicates"] >= 0.95, f"Replay detection rate too low: {rg['detection_rate_on_duplicates']}"

    # 4. autofill_desktop false-positive rate
    fpr_sub = metrics.get("false_positive_rate_by_human_subgroup", {})
    assert "autofill_desktop" in fpr_sub, "autofill_desktop missing from human subgroups"
    af = fpr_sub["autofill_desktop"]
    assert "fpr_min_p50" in af
    assert "fpr_full_p50" in af
    assert 0.0 <= af["fpr_min_p50"] <= 1.0


def test_replay_guard_live_endpoint(client):
    """
    Live endpoint test:
    Submitting the exact same feature vector within TTL is rejected with 400.
    """
    feats = {k: 123.456 for k in get_required_features("min")}
    res1 = client.post("/api/session", json={
        "site_key": "test_site",
        "features": feats,
        "access_needs": []
    })
    assert res1.status_code == 200

    # Submit identical vector
    res2 = client.post("/api/session", json={
        "site_key": "test_site",
        "features": feats,
        "access_needs": []
    })
    assert res2.status_code == 400, f"Expected 400 for replayed feature vector, got {res2.status_code}"
    assert "replay" in res2.json().get("detail", "").lower()
