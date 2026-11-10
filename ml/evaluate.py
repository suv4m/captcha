import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import json
import joblib
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple

from backend.app.config import ARTIFACTS_DIR, CATALOG_PATH
from ml.simulate import generate_population, HUMAN_SUBGROUPS, ALL_BOT_TYPES
from ml.train import extract_dataset, TEST_SEED

with open(CATALOG_PATH, "r", encoding="utf-8") as f:
    CATALOG = json.load(f)

CHALLENGES = {c["id"]: c for c in CATALOG["challenges"]}
INCOMPAT_PENALTY = CATALOG["incompatible_penalty"]

def select_challenge(p: float, declared_needs: List[str], B: float = 60.0,
                     filter_accessible: bool = True) -> str:
    """
    Select optimal challenge c* minimizing:
    J(c) = (1 - p) * [T(c)/10 + 3 * (1 - Sh(c))] + p * B * Sb(c)
    Break ties by lower T.
    """
    needs_set = set(declared_needs)
    has_cognitive = "cognitive" in needs_set

    best_id = "none"
    best_cost = float("inf")
    best_T = float("inf")

    for cid, c in CHALLENGES.items():
        if filter_accessible:

            if has_cognitive and c["level"] == 3:
                continue

            if not needs_set.isdisjoint(c["incompatible_with"]):
                continue

        T = c["T"]
        Sh = c["Sh"]
        Sb = c["Sb"]
        human_cost = (T / 10.0) + 3.0 * (1.0 - Sh)
        bot_cost = B * Sb
        cost = (1.0 - p) * human_cost + p * bot_cost

        if cost < best_cost - 1e-9:
            best_cost = cost
            best_id = cid
            best_T = T
        elif abs(cost - best_cost) <= 1e-9:
            if T < best_T:
                best_cost = cost
                best_id = cid
                best_T = T

    return best_id

def simulate_session(is_bot: int, subgroup: str, access_needs: List[str],
                     chosen_id: str, rng: np.random.RandomState) -> Dict[str, Any]:
    c = CHALLENGES[chosen_id]
    needs_set = set(access_needs)

    is_violation = False
    if not is_bot:
        if not needs_set.isdisjoint(c["incompatible_with"]):
            is_violation = True
            Sh = INCOMPAT_PENALTY["Sh"]
            T = INCOMPAT_PENALTY["T"]
        else:
            Sh = c["Sh"]
            T = c["T"]
        passed = bool(rng.random() < Sh)
        time_spent = T
    else:
        passed = bool(rng.random() < c["Sb"])
        time_spent = c["T"]

    return {
        "passed": passed,
        "time_spent": time_spent,
        "is_violation": is_violation,
        "is_free": (chosen_id == "none" or c.get("invisible", False))
    }

def evaluate_all(n_runs: int = 20, breach_cost: float = 2.0):
    print("[evaluate.py] Loading models and generating test population...")
    cal_full = joblib.load(ARTIFACTS_DIR / "risk_full.joblib")
    cal_min = joblib.load(ARTIFACTS_DIR / "risk_min.joblib")

    with open(ARTIFACTS_DIR / "feature_sets.json", "r", encoding="utf-8") as f:
        feature_sets = json.load(f)
    min_indices = feature_sets["min"]["indices"]

    test_traces = generate_population(TEST_SEED, 3000, 3000, is_test=True)
    X_test, y_test, meta_test = extract_dataset(test_traces)
    X_test_min = X_test[:, min_indices]

    p_full = cal_full.predict_proba(X_test)[:, 1]
    p_min = cal_min.predict_proba(X_test_min)[:, 1]

    subgroups = np.array([m["subgroup"] for m in meta_test])

    needs_keys = ["vision", "hearing", "motor", "cognitive"]
    needs_mat = np.zeros((len(meta_test), 4), dtype=np.int8)
    for i, m in enumerate(meta_test):
        for j, k in enumerate(needs_keys):
            if k in m.get("access_needs", []):
                needs_mat[i, j] = 1

    np.savez_compressed(
        ARTIFACTS_DIR / "test_scores.npz",
        y_test=y_test,
        p_full=p_full,
        p_min=p_min,
        subgroups=subgroups,
        needs_mat=needs_mat
    )
    print(f"  Saved vectorized test scores to {ARTIFACTS_DIR / 'test_scores.npz'}")

    policies = ["P0", "P1", "P2", "P3"]
    policy_names = {
        "P0": "P0: Fixed (vis2)",
        "P1": "P1: Adaptive (Full, unconstrained)",
        "P2": "P2: Adaptive + Accessible (Full)",
        "P3": "P3: Adaptive + Accessible + Private (Min)"
    }
    bytes_per_session = {
        "P0": 0,
        "P1": 216,
        "P2": 216,
        "P3": 68
    }

    results = {}
    print(f"[evaluate.py] Running policy evaluation over {n_runs} seeded Monte Carlo runs (B={breach_cost})...")

    for pol in policies:
        run_metrics = {
            "human_pass_rate": [],
            "mean_human_time": [],
            "bot_pass_rate": [],
            "security_rate": [],
            "challenge_free_rate": [],
            "a11y_violation_rate": [],
            "human_block_rate_by_subgroup": {sg: [] for sg in HUMAN_SUBGROUPS}
        }

        for run in range(n_runs):
            rng = np.random.RandomState(run + 42)
            n_humans = 0
            n_bots = 0
            human_passed = 0
            bot_passed = 0
            total_human_time = 0.0
            free_sessions = 0
            violations = 0
            sg_totals = {sg: 0 for sg in HUMAN_SUBGROUPS}
            sg_blocks = {sg: 0 for sg in HUMAN_SUBGROUPS}

            for i in range(len(meta_test)):
                is_bot = int(y_test[i])
                meta = meta_test[i]
                sg = meta["subgroup"]
                needs = meta.get("access_needs", [])

                if pol == "P0":
                    cid = "vis2"
                elif pol == "P1":
                    p = float(p_full[i])
                    cid = select_challenge(p, needs, B=breach_cost, filter_accessible=False)
                elif pol == "P2":
                    p = float(p_full[i])
                    cid = select_challenge(p, needs, B=breach_cost, filter_accessible=True)
                elif pol == "P3":
                    p = float(p_min[i])
                    cid = select_challenge(p, needs, B=breach_cost, filter_accessible=True)

                sim = simulate_session(is_bot, sg, needs, cid, rng)

                if is_bot:
                    n_bots += 1
                    if sim["passed"]:
                        bot_passed += 1
                else:
                    n_humans += 1
                    total_human_time += sim["time_spent"]
                    if sim["passed"]:
                        human_passed += 1
                    else:
                        sg_blocks[sg] += 1
                    sg_totals[sg] += 1
                    if sim["is_violation"]:
                        violations += 1
                    if sim["is_free"]:
                        free_sessions += 1

            run_metrics["human_pass_rate"].append(human_passed / max(1, n_humans))
            run_metrics["mean_human_time"].append(total_human_time / max(1, n_humans))
            b_pass = bot_passed / max(1, n_bots)
            run_metrics["bot_pass_rate"].append(b_pass)
            run_metrics["security_rate"].append(1.0 - b_pass)
            run_metrics["challenge_free_rate"].append(free_sessions / max(1, n_humans))
            run_metrics["a11y_violation_rate"].append(violations / max(1, n_humans))

            for sg in HUMAN_SUBGROUPS:
                tot = sg_totals[sg]
                blk = sg_blocks[sg]
                run_metrics["human_block_rate_by_subgroup"][sg].append(blk / max(1, tot))

        summary = {
            "name": policy_names[pol],
            "bytes_collected": bytes_per_session[pol],
            "human_pass_rate": {
                "mean": round(float(np.mean(run_metrics["human_pass_rate"])), 4),
                "std": round(float(np.std(run_metrics["human_pass_rate"])), 4)
            },
            "mean_human_time_s": {
                "mean": round(float(np.mean(run_metrics["mean_human_time"])), 2),
                "std": round(float(np.std(run_metrics["mean_human_time"])), 2)
            },
            "bot_pass_rate": {
                "mean": round(float(np.mean(run_metrics["bot_pass_rate"])), 4),
                "std": round(float(np.std(run_metrics["bot_pass_rate"])), 4)
            },
            "security_rate": {
                "mean": round(float(np.mean(run_metrics["security_rate"])), 4),
                "std": round(float(np.std(run_metrics["security_rate"])), 4)
            },
            "challenge_free_rate": {
                "mean": round(float(np.mean(run_metrics["challenge_free_rate"])), 4),
                "std": round(float(np.std(run_metrics["challenge_free_rate"])), 4)
            },
            "a11y_violation_rate": {
                "mean": round(float(np.mean(run_metrics["a11y_violation_rate"])), 4),
                "std": round(float(np.std(run_metrics["a11y_violation_rate"])), 4)
            },
            "human_block_rate_by_subgroup": {
                sg: {
                    "mean": round(float(np.mean(run_metrics["human_block_rate_by_subgroup"][sg])), 4),
                    "std": round(float(np.std(run_metrics["human_block_rate_by_subgroup"][sg])), 4)
                }
                for sg in HUMAN_SUBGROUPS
            }
        }
        results[pol] = summary
        print(f"   {pol}: HumanPass={summary['human_pass_rate']['mean']*100:.1f}%, MeanTime={summary['mean_human_time_s']['mean']:.1f}s, Security={summary['security_rate']['mean']*100:.1f}%, A11yViol={summary['a11y_violation_rate']['mean']*100:.2f}%, Free={summary['challenge_free_rate']['mean']*100:.1f}%")

    with open(ARTIFACTS_DIR / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"  Results saved to {ARTIFACTS_DIR / 'results.json'}")
    return results

if __name__ == "__main__":
    evaluate_all()
