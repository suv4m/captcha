import sys
import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.simulate import generate_bot_trace, generate_human_trace, ALL_BOT_TYPES
from ml.extract import extract_features
from backend.app.risk import score_session_risk
from backend.app.decision import select_best_challenge


def run_bot_demo(runs_per_type: int = 5):
    print("=" * 60)
    print("  BOT DEMO: Evaluating Bot Archetypes Against Risk Model")
    print("=" * 60)

    rng = random.Random(42)
    # Generate human corpus for replay
    human_corpus = [generate_human_trace(rng, "desktop_mouse") for _ in range(10)]

    for btype in ["instant", "linear", "noisy", "humanized", "replay"]:
        print(f"\n--- Testing Bot Archetype: [{btype.upper()}] ---")
        scores = []
        chosen_types = []

        for _ in range(runs_per_type):
            tr = generate_bot_trace(rng, btype, human_corpus=human_corpus)
            feats = extract_features(tr)
            # Evaluate with MIN model (the live production default)
            p = score_session_risk(feats, mode="min")
            scores.append(p)

            decision = select_best_challenge(p, access_needs=[], B=60.0)
            chosen_types.append(decision["chosen_type"])

        mean_p = sum(scores) / len(scores)
        print(f"  Risk Scores (p)    : {[round(s, 3) for s in scores]}")
        print(f"  Mean Risk (p)      : {mean_p:.4f} (Band: {'HIGH' if mean_p >= 0.65 else 'MED' if mean_p >= 0.15 else 'LOW'})")
        print(f"  Chosen Challenges  : {chosen_types}")

        if btype in ["instant", "linear", "noisy"]:
            assert mean_p > 0.85, f"Expected high risk for simple bot {btype}, got {mean_p}"
            print(f"  Result: Successfully routed to strong challenge/blocked.")
        elif btype == "humanized":
            print(f"  Result: Unseen sophisticated bot reported honestly (Score: {mean_p:.3f}).")
        elif btype == "replay":
            print(f"  Result: Replay attack evaluated (Score: {mean_p:.3f}).")

    print("\nBot demo evaluation completed successfully!")


if __name__ == "__main__":
    run_bot_demo()

