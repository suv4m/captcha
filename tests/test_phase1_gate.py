import json
import joblib
import numpy as np
from pathlib import Path
import pytest

from backend.app.config import ARTIFACTS_DIR
from ml.train import TRAIN_SEED, VAL_SEED, TEST_SEED

def test_artifacts_exist():
    expected_files = [
        "risk_full.joblib",
        "risk_min.joblib",
        "feature_sets.json",
        "metrics.json",
        "results.json",
        "test_scores.npz"
    ]
    for fname in expected_files:
        p = ARTIFACTS_DIR / fname
        assert p.exists(), f"Missing artifact: {p}"
        assert p.stat().st_size > 0, f"Artifact is empty: {p}"

def test_seeds_disjoint():
    seeds = {TRAIN_SEED, VAL_SEED, TEST_SEED}
    assert len(seeds) == 3, "Train, val, and test seeds must be strictly disjoint!"

def test_ml_sanity_10_2():
    with open(ARTIFACTS_DIR / "metrics.json", "r", encoding="utf-8") as f:
        metrics = json.load(f)

    shuffle_auc = metrics["label_shuffle_test_auc"]
    assert 0.45 <= shuffle_auc <= 0.55, f"Label shuffle AUC out of bounds: {shuffle_auc}"

    full_auc = metrics["full_model"]["roc_auc"]
    min_auc = metrics["min_model"]["roc_auc"]
    assert full_auc < 0.995, f"Defect: Test AUC >= 0.995 indicating trivial simulator/leakage: {full_auc}"
    assert min_auc < 0.995, f"Defect: Test MIN AUC >= 0.995: {min_auc}"
    assert full_auc > 0.70, f"Model underperforming: {full_auc}"
    assert min_auc > 0.70, f"MIN model underperforming: {min_auc}"

    ece = metrics["min_model"]["ece"]
    assert ece is not None and ece > 0.0

    recalls = metrics["recall_by_bot_type"]
    assert "humanized" in recalls
    assert recalls["humanized"]["is_unseen"] is True

    assert 0.0 <= recalls["humanized"]["recall_min_p50"] <= 1.0

    fprs = metrics["false_positive_rate_by_human_subgroup"]
    for sg in ["desktop_mouse", "touch_mobile", "keyboard_assistive", "motor_tremor"]:
        assert sg in fprs
        assert 0.0 <= fprs[sg]["fpr_min_p50"] <= 0.20

    with open(ARTIFACTS_DIR / "feature_sets.json", "r", encoding="utf-8") as f:
        fsets = json.load(f)
    assert fsets["full"]["count"] == 25
    assert fsets["min"]["count"] == 8

def test_test_scores_npz():
    npz = np.load(ARTIFACTS_DIR / "test_scores.npz")
    assert "y_test" in npz
    assert "p_full" in npz
    assert "p_min" in npz
    assert "subgroups" in npz
    assert "needs_mat" in npz
    assert len(npz["y_test"]) == 6000
    assert len(npz["p_full"]) == 6000
    assert len(npz["p_min"]) == 6000

