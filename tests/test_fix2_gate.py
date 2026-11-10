from collections import Counter
import numpy as np
import pytest
import json

from backend.app.config import ARTIFACTS_DIR, CATALOG_PATH, DEFAULT_BREACH_COST
from backend.app.decision import select_best_challenge

def test_human_mix_not_more_than_50_percent_single_challenge():
    """Gate test: At chosen DEFAULT_BREACH_COST, human mix is not more than 50% single-challenge."""
    npz_path = ARTIFACTS_DIR / "test_scores.npz"
    data = np.load(npz_path, allow_pickle=True)
    y_test = data["y_test"]
    p_min = data["p_min"]
    human_p = p_min[y_test == 0]

    chosen = [
        select_best_challenge(float(p), access_needs=[], B=DEFAULT_BREACH_COST)["chosen_id"]
        for p in human_p
    ]
    counts = Counter(chosen)
    n_humans = len(human_p)
    shares = {cid: cnt / n_humans for cid, cnt in counts.items()}

    most_common_cid, most_common_cnt = counts.most_common(1)[0]
    max_share = most_common_cnt / n_humans

    if most_common_cid == "none":
        assert max_share >= 0.50, "Expected most humans to receive 'none' or invisible PoW"
    else:
        assert max_share <= 0.50, (
            f"At DEFAULT_BREACH_COST={DEFAULT_BREACH_COST}, single-challenge '{most_common_cid}' "
            f"has {max_share * 100:.1f}% share, exceeding 50% limit! Full shares: {shares}"
        )

def test_bots_with_high_risk_never_receive_none_or_pow1():
    """Gate test: Bots with p > 0.9 never receive 'none' or 'pow1' at DEFAULT_BREACH_COST."""
    needs_combos = [
        [],
        ["vision"],
        ["hearing"],
        ["motor"],
        ["cognitive"],
        ["vision", "hearing"],
        ["vision", "motor"],
        ["hearing", "motor"]
    ]
    for p in [0.901, 0.92, 0.95, 0.98, 0.999]:
        for needs in needs_combos:
            res = select_best_challenge(p, access_needs=needs, B=DEFAULT_BREACH_COST)
            cid = res["chosen_id"]
            assert cid not in ["none", "pow1"], (
                f"Bot with p={p} and needs={needs} received weak challenge '{cid}'!"
            )

def test_catalog_pow_invisible_flag():
    """Verify pow1 and pow2 in catalog.json are marked invisible."""
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    cmap = {c["id"]: c for c in catalog["challenges"]}
    assert cmap["pow1"].get("invisible") is True
    assert cmap["pow2"].get("invisible") is True
    assert cmap["pow3"].get("invisible", False) is False

