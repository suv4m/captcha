import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import FEATURES_PATH, CATALOG_PATH

def test_features_json_sanity():
    assert FEATURES_PATH.exists()
    with open(FEATURES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    features = data["features"]
    assert len(features) == 25
    expected_names = [
        "p_n_moves", "p_path_len", "p_straightness", "p_speed_mean", "p_speed_std",
        "p_speed_max", "p_acc_std", "p_dir_changes_per_100px", "p_pauses", "p_dt_std",
        "p_clicks", "p_click_gap_std", "k_n", "k_gap_mean", "k_gap_std",
        "k_backspaces", "t_since_mount", "t_first_interaction", "t_idle_ratio", "t_scrolls",
        "t_focus_changes", "t_events_total", "d_pointer_mouse", "d_pointer_touch", "d_pointer_none"
    ]
    actual_names = [feat["name"] for feat in features]
    assert actual_names == expected_names
    for i, feat in enumerate(features):
        assert feat["index"] == i
        assert feat["id"] == i + 1

def test_catalog_json_sanity():
    assert CATALOG_PATH.exists()
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    assert "_disclaimer" in catalog
    assert catalog["incompatible_penalty"]["Sh"] == 0.12
    assert catalog["incompatible_penalty"]["T"] == 45.0
    challenges = catalog["challenges"]
    assert len(challenges) == 13
    ids = [c["id"] for c in challenges]
    assert ids == [
        "none", "pow1", "pow2", "pow3", "vis1", "vis2", "vis3",
        "aud1", "aud2", "aud3", "drg1", "drg2", "drg3"
    ]

def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "version" in payload

