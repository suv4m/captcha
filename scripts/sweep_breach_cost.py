import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import json
import numpy as np
from backend.app.config import ARTIFACTS_DIR, CATALOG_PATH
from ml.evaluate import CHALLENGES, INCOMPAT_PENALTY, select_challenge, simulate_session

def run_sweep():

    npz_path = ARTIFACTS_DIR / "test_scores.npz"
    if not npz_path.exists():
        print(f"Error: {npz_path} does not exist.")
        return
    data = np.load(npz_path, allow_pickle=True)
    y_test = data["y_test"]
    p_min = data["p_min"]
    subgroups = data["subgroups"]
    needs_mat = data["needs_mat"]
    needs_keys = ["vision", "hearing", "motor", "cognitive"]

    N = len(y_test)
    human_indices = np.where(y_test == 0)[0]
    bot_indices = np.where(y_test == 1)[0]
    n_humans = len(human_indices)
    n_bots = len(bot_indices)

    needs_list = []
    for i in range(N):
        n_arr = [needs_keys[j] for j in range(4) if needs_mat[i, j] == 1]
        needs_list.append(n_arr)

    B_values = [2, 3, 5, 8, 12, 20, 40, 60]
    print(f"{'B':>3} | {'MeanTime':>8} | {'HumanPass':>9} | {'Security':>8} | {'Free/Invis':>10} | Challenge Distribution (Humans)")
    print("-" * 90)

    sweep_results = []

    for B in B_values:

        chosen_ids = []
        for i in range(N):
            cid = select_challenge(float(p_min[i]), needs_list[i], B=float(B), filter_accessible=True)
            chosen_ids.append(cid)

        human_cids = [chosen_ids[idx] for idx in human_indices]
        human_times = []
        human_passes = []
        human_free_count = 0

        cid_counts = {}
        for cid in human_cids:
            cid_counts[cid] = cid_counts.get(cid, 0) + 1
            c = CHALLENGES[cid]
            if cid == "none" or c.get("invisible", False):
                human_free_count += 1

        rng = np.random.RandomState(42)
        total_time = 0.0
        total_pass = 0
        n_trials = 20

        for r in range(n_trials):
            for idx in human_indices:
                res = simulate_session(0, subgroups[idx], needs_list[idx], chosen_ids[idx], rng)
                total_time += res["time_spent"]
                if res["passed"]:
                    total_pass += 1

        mean_time = total_time / (n_humans * n_trials)
        pass_rate = total_pass / (n_humans * n_trials)
        free_ratio = human_free_count / n_humans

        bot_passes = 0
        for r in range(n_trials):
            for idx in bot_indices:
                res = simulate_session(1, subgroups[idx], needs_list[idx], chosen_ids[idx], rng)
                if res["passed"]:
                    bot_passes += 1
        bot_pass_rate = bot_passes / (n_bots * n_trials)
        security = 1.0 - bot_pass_rate

        dist_str = ", ".join([f"{k}:{v/n_humans*100:.1f}%" for k, v in sorted(cid_counts.items(), key=lambda x: -x[1])[:4]])

        print(f"{B:>3} | {mean_time:>7.1f}s | {pass_rate*100:>8.1f}% | {security*100:>7.1f}% | {free_ratio*100:>9.1f}% | {dist_str}")

        sweep_results.append({
            "B": B,
            "mean_human_time": round(mean_time, 2),
            "human_pass_rate": round(pass_rate, 4),
            "security": round(security, 4),
            "challenge_free_ratio": round(free_ratio, 4),
            "challenge_counts": {k: round(v / n_humans, 4) for k, v in cid_counts.items()}
        })

    out_path = ARTIFACTS_DIR / "b_sweep.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sweep_results, f, indent=2)
    print(f"\n[sweep_breach_cost] Saved sweep results to {out_path}")

    return sweep_results

if __name__ == "__main__":
    run_sweep()
