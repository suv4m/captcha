import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import json
import time
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple

from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV, FrozenEstimator
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    roc_auc_score, average_precision_score, brier_score_loss, roc_curve
)

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

from backend.app.config import ARTIFACTS_DIR, FEATURES_PATH
from ml.simulate import (
    generate_population, HUMAN_SUBGROUPS, ALL_BOT_TYPES
)
from ml.extract import extract_features, FEATURE_NAMES

TRAIN_SEED = 101
VAL_SEED = 202
TEST_SEED = 303

assert len({TRAIN_SEED, VAL_SEED, TEST_SEED}) == 3, "Seeds must be disjoint!"

def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    bin_limits = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        low, high = bin_limits[i], bin_limits[i + 1]
        if i == n_bins - 1:
            mask = (y_prob >= low) & (y_prob <= high)
        else:
            mask = (y_prob >= low) & (y_prob < high)
        bin_size = np.sum(mask)
        if bin_size > 0:
            bin_acc = np.mean(y_true[mask])
            bin_conf = np.mean(y_prob[mask])
            ece += (bin_size / n) * abs(bin_acc - bin_conf)
    return float(ece)

def compute_tpr_at_fpr(y_true: np.ndarray, y_prob: np.ndarray, target_fpr: float = 0.01) -> float:
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    valid_tpr = tpr[fpr <= target_fpr]
    return float(np.max(valid_tpr)) if len(valid_tpr) > 0 else 0.0

def extract_dataset(traces: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, Any]]]:
    X_list = []
    y_list = []
    meta_list = []
    for tr in traces:
        feats = extract_features(tr)
        X_list.append(feats)
        y_list.append(tr["meta"]["is_bot"])
        meta_list.append(tr["meta"])
    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.int32), meta_list

def train_all():
    print("[train.py] Starting synthetic dataset generation...")
    t0 = time.time()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    print("  Generating train set (6000 humans, 6000 bots)...")
    train_traces = generate_population(TRAIN_SEED, 6000, 6000, is_test=False)
    print("  Generating val set (1500 humans, 1500 bots)...")
    val_traces = generate_population(VAL_SEED, 1500, 1500, is_test=False)
    print("  Generating test set (3000 humans, 3000 bots)...")
    test_traces = generate_population(TEST_SEED, 3000, 3000, is_test=True)

    X_train, y_train, meta_train = extract_dataset(train_traces)
    X_val, y_val, meta_val = extract_dataset(val_traces)
    X_test, y_test, meta_test = extract_dataset(test_traces)

    print(f"  Dataset extracted in {time.time() - t0:.2f}s")
    print(f"  X_train: {X_train.shape}, X_val: {X_val.shape}, X_test: {X_test.shape}")

    print("[train.py] Comparing candidate classifiers...")
    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=3, class_weight="balanced", random_state=42, n_jobs=-1
        ),
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42))
        ]),
        "HistGradientBoosting": HistGradientBoostingClassifier(random_state=42),
    }
    if HAS_XGB:
        models["XGBoost"] = XGBClassifier(
            n_estimators=150, max_depth=5, learning_rate=0.1, random_state=42,
            eval_metric="logloss", n_jobs=-1
        )

    comparison_results = []
    for name, clf in models.items():
        t_m0 = time.time()
        clf.fit(X_train, y_train)
        fit_time = time.time() - t_m0
        val_probs = clf.predict_proba(X_val)[:, 1]
        val_auc = float(roc_auc_score(y_val, val_probs))
        val_pr_auc = float(average_precision_score(y_val, val_probs))
        comparison_results.append({
            "model": name,
            "val_roc_auc": round(val_auc, 4),
            "val_pr_auc": round(val_pr_auc, 4),
            "fit_time_s": round(fit_time, 2)
        })
        print(f"   - {name}: Val AUC = {val_auc:.4f}, Val PR-AUC = {val_pr_auc:.4f} ({fit_time:.2f}s)")

    print("[train.py] Fitting primary RandomForest (FULL features)...")
    base_rf_full = RandomForestClassifier(
        n_estimators=300, min_samples_leaf=3, class_weight="balanced", random_state=42, n_jobs=-1
    )
    base_rf_full.fit(X_train, y_train)

    print("[train.py] Calibrating FULL model with Sigmoid / Isotonic on Val split...")
    cal_full = CalibratedClassifierCV(
        estimator=FrozenEstimator(base_rf_full), method="sigmoid"
    )
    cal_full.fit(X_val, y_val)

    print("[train.py] Selecting 8 MIN features via permutation importance on Val split...")
    perm_res = permutation_importance(
        base_rf_full, X_val, y_val, n_repeats=5, random_state=42, n_jobs=-1
    )
    importances = perm_res.importances_mean
    sorted_idx = np.argsort(importances)[::-1]
    min_feature_indices = sorted_idx[:8].tolist()
    min_feature_names = [FEATURE_NAMES[i] for i in min_feature_indices]
    print("  Selected MIN features:", min_feature_names)

    feature_sets = {
        "full": {
            "count": len(FEATURE_NAMES),
            "names": FEATURE_NAMES,
            "indices": list(range(len(FEATURE_NAMES)))
        },
        "min": {
            "count": len(min_feature_names),
            "names": min_feature_names,
            "indices": min_feature_indices
        }
    }
    with open(ARTIFACTS_DIR / "feature_sets.json", "w", encoding="utf-8") as f:
        json.dump(feature_sets, f, indent=2)

    print("[train.py] Fitting and calibrating MIN model...")
    X_train_min = X_train[:, min_feature_indices]
    X_val_min = X_val[:, min_feature_indices]
    X_test_min = X_test[:, min_feature_indices]

    base_rf_min = RandomForestClassifier(
        n_estimators=300, min_samples_leaf=3, class_weight="balanced", random_state=42, n_jobs=-1
    )
    base_rf_min.fit(X_train_min, y_train)

    cal_min = CalibratedClassifierCV(
        estimator=FrozenEstimator(base_rf_min), method="sigmoid"
    )
    cal_min.fit(X_val_min, y_val)

    joblib.dump(cal_full, ARTIFACTS_DIR / "risk_full.joblib")
    joblib.dump(cal_min, ARTIFACTS_DIR / "risk_min.joblib")
    print(f"  Saved {ARTIFACTS_DIR / 'risk_full.joblib'} and {ARTIFACTS_DIR / 'risk_min.joblib'}")

    print("[train.py] Evaluating on held-out test population...")
    test_probs_full = cal_full.predict_proba(X_test)[:, 1]
    test_probs_min = cal_min.predict_proba(X_test_min)[:, 1]

    auc_full = float(roc_auc_score(y_test, test_probs_full))
    auc_min = float(roc_auc_score(y_test, test_probs_min))
    pr_auc_full = float(average_precision_score(y_test, test_probs_full))
    pr_auc_min = float(average_precision_score(y_test, test_probs_min))
    tpr_at_1fpr_full = compute_tpr_at_fpr(y_test, test_probs_full, 0.01)
    tpr_at_1fpr_min = compute_tpr_at_fpr(y_test, test_probs_min, 0.01)
    brier_full = float(brier_score_loss(y_test, test_probs_full))
    brier_min = float(brier_score_loss(y_test, test_probs_min))
    ece_full = compute_ece(y_test, test_probs_full, n_bins=10)
    ece_min = compute_ece(y_test, test_probs_min, n_bins=10)

    print(f"  Test FULL: AUC={auc_full:.4f}, PR-AUC={pr_auc_full:.4f}, ECE={ece_full:.4f}, TPR@1%FPR={tpr_at_1fpr_full:.4f}")
    print(f"  Test MIN : AUC={auc_min:.4f}, PR-AUC={pr_auc_min:.4f}, ECE={ece_min:.4f}, TPR@1%FPR={tpr_at_1fpr_min:.4f}")

    if auc_full >= 0.995 or auc_min >= 0.995:
        print("  WARNING: AUC >= 0.995 detected! Simulator parameter overlap required.")

    y_test_shuffled = np.random.RandomState(42).permutation(y_test)
    shuffle_auc = float(roc_auc_score(y_test_shuffled, test_probs_full))
    print(f"  Label-shuffle test AUC: {shuffle_auc:.4f} (assert 0.50 +- 0.05: {0.45 <= shuffle_auc <= 0.55})")

    recall_by_bot_type = {}
    test_subgroups = [m["subgroup"] for m in meta_test]
    for btype in ALL_BOT_TYPES:
        mask = [i for i, m in enumerate(meta_test) if m["is_bot"] == 1 and m["subgroup"] == btype]
        if len(mask) > 0:

            rec_full = float(np.mean(test_probs_full[mask] > 0.5))
            rec_min = float(np.mean(test_probs_min[mask] > 0.5))
            recall_by_bot_type[btype] = {
                "count": len(mask),
                "recall_full_p50": round(rec_full, 4),
                "recall_min_p50": round(rec_min, 4),
                "mean_score_full": round(float(np.mean(test_probs_full[mask])), 4),
                "mean_score_min": round(float(np.mean(test_probs_min[mask])), 4),
                "is_unseen": (btype == "humanized")
            }
            print(f"   Bot [{btype}]: recall={rec_full:.4f} (mean p={np.mean(test_probs_full[mask]):.3f}) [unseen={btype=='humanized'}]")

    fpr_by_human_subgroup = {}
    for sg in HUMAN_SUBGROUPS:
        mask = [i for i, m in enumerate(meta_test) if m["is_bot"] == 0 and m["subgroup"] == sg]
        if len(mask) > 0:

            fp_full = float(np.mean(test_probs_full[mask] > 0.5))
            fp_min = float(np.mean(test_probs_min[mask] > 0.5))
            fpr_by_human_subgroup[sg] = {
                "count": len(mask),
                "fpr_full_p50": round(fp_full, 4),
                "fpr_min_p50": round(fp_min, 4),
                "mean_score_full": round(float(np.mean(test_probs_full[mask])), 4),
                "mean_score_min": round(float(np.mean(test_probs_min[mask])), 4),
            }
            print(f"   Human [{sg}]: FPR={fp_full:.4f} (mean p={np.mean(test_probs_full[mask]):.3f})")

    auc_vs_k = {}
    for k in [4, 6, 8, 12, 25]:
        top_k_indices = sorted_idx[:k].tolist()
        rf_k = RandomForestClassifier(
            n_estimators=100, min_samples_leaf=3, class_weight="balanced", random_state=42, n_jobs=-1
        )
        rf_k.fit(X_train[:, top_k_indices], y_train)
        p_k = rf_k.predict_proba(X_test[:, top_k_indices])[:, 1]
        auc_k = float(roc_auc_score(y_test, p_k))
        auc_vs_k[str(k)] = round(auc_k, 4)
        print(f"   Top-{k} features AUC: {auc_k:.4f}")

    fpr_raw, tpr_raw, _ = roc_curve(y_test, test_probs_min)
    step = max(1, len(fpr_raw) // 50)
    roc_points = [
        {"fpr": round(float(fpr_raw[i]), 4), "tpr": round(float(tpr_raw[i]), 4)}
        for i in range(0, len(fpr_raw), step)
    ]
    if roc_points[-1]["fpr"] < 1.0:
        roc_points.append({"fpr": 1.0, "tpr": 1.0})

    no_replay_mask = [i for i, m in enumerate(meta_test) if m.get("subgroup") != "replay"]
    y_test_no_replay = y_test[no_replay_mask]
    auc_full_no_replay = float(roc_auc_score(y_test_no_replay, test_probs_full[no_replay_mask]))
    auc_min_no_replay = float(roc_auc_score(y_test_no_replay, test_probs_min[no_replay_mask]))
    print(f"  Test FULL without replay: AUC={auc_full_no_replay:.4f}")
    print(f"  Test MIN  without replay: AUC={auc_min_no_replay:.4f}")

    from backend.app.store import Storage
    test_store = Storage()
    detected_count = 0
    sample_vectors = X_test[:100]
    for row in sample_vectors:
        feat_dict = {FEATURE_NAMES[idx]: float(val) for idx, val in enumerate(row)}
        test_store.check_replay(feat_dict)
        if test_store.check_replay(feat_dict):
            detected_count += 1
    replay_guard_detection_rate = detected_count / len(sample_vectors)

    metrics = {
        "_disclaimer": "Simulated population with assumed parameters. Not real-world bot resistance.",
        "dataset_sizes": {
            "train": len(train_traces),
            "val": len(val_traces),
            "test": len(test_traces)
        },
        "seeds": {
            "train": TRAIN_SEED,
            "val": VAL_SEED,
            "test": TEST_SEED
        },
        "models_compared": comparison_results,
        "full_model": {
            "feature_count": 25,
            "roc_auc": round(auc_full, 4),
            "roc_auc_with_replay": round(auc_full, 4),
            "roc_auc_without_replay": round(auc_full_no_replay, 4),
            "pr_auc": round(pr_auc_full, 4),
            "tpr_at_1pct_fpr": round(tpr_at_1fpr_full, 4),
            "brier_score": round(brier_full, 4),
            "ece": round(ece_full, 4),
        },
        "min_model": {
            "feature_count": 8,
            "selected_features": min_feature_names,
            "roc_auc": round(auc_min, 4),
            "roc_auc_with_replay": round(auc_min, 4),
            "roc_auc_without_replay": round(auc_min_no_replay, 4),
            "pr_auc": round(pr_auc_min, 4),
            "tpr_at_1pct_fpr": round(tpr_at_1fpr_min, 4),
            "brier_score": round(brier_min, 4),
            "ece": round(ece_min, 4),
        },
        "auc_with_and_without_replay": {
            "full_with_replay": round(auc_full, 4),
            "full_without_replay": round(auc_full_no_replay, 4),
            "min_with_replay": round(auc_min, 4),
            "min_without_replay": round(auc_min_no_replay, 4),
        },
        "replay_guard": {
            "detection_rate_on_duplicates": round(replay_guard_detection_rate, 4),
            "ttl_seconds": 300
        },
        "label_shuffle_test_auc": round(shuffle_auc, 4),
        "recall_by_bot_type": recall_by_bot_type,
        "false_positive_rate_by_human_subgroup": fpr_by_human_subgroup,
        "autofill_desktop": fpr_by_human_subgroup.get("autofill_desktop", {}),
        "auc_vs_feature_count": auc_vs_k,
        "roc_curve_points": roc_points
    }

    with open(ARTIFACTS_DIR / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"  Metrics successfully saved to {ARTIFACTS_DIR / 'metrics.json'}")

    return {
        "cal_full": cal_full,
        "cal_min": cal_min,
        "test_probs_full": test_probs_full,
        "test_probs_min": test_probs_min,
        "meta_test": meta_test,
        "y_test": y_test,
        "metrics": metrics
    }

if __name__ == "__main__":
    train_all()
