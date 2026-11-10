import json
from typing import Dict, Any, List, Tuple, Optional, Set
from backend.app.config import CATALOG_PATH, DEFAULT_BREACH_COST

with open(CATALOG_PATH, "r", encoding="utf-8") as f:
    _CATALOG_DATA = json.load(f)

CATALOG_CHALLENGES: List[Dict[str, Any]] = _CATALOG_DATA["challenges"]
CHALLENGE_MAP: Dict[str, Dict[str, Any]] = {c["id"]: c for c in CATALOG_CHALLENGES}
INCOMPATIBLE_PENALTY: Dict[str, Any] = _CATALOG_DATA.get("incompatible_penalty", {"Sh": 0.12, "T": 45.0})


def get_compatible_challenges(access_needs: List[str], exclude_type: Optional[str] = None) -> List[Dict[str, Any]]:
    needs_set = set(access_needs)
    has_cognitive = "cognitive" in needs_set

    compatible = []
    for c in CATALOG_CHALLENGES:
        if c["id"] == "none":
            continue
        if exclude_type and c["type"] == exclude_type:
            continue
        # If cognitive is declared, drop all level-3 entries
        if has_cognitive and c["level"] == 3:
            continue
        # Drop if incompatible with any declared need
        if not needs_set.isdisjoint(c["incompatible_with"]):
            continue
        compatible.append(c)

    # Invariant I3: Proof-of-work is compatible with everyone.
    # If all other types were excluded or filtered, ensure PoW remains
    if not compatible:
        for c in CATALOG_CHALLENGES:
            if c["type"] == "pow":
                if has_cognitive and c["level"] == 3:
                    continue
                compatible.append(c)

    return compatible


def compute_cost(c: Dict[str, Any], p: float, B: float) -> float:
    T = c["T"]
    Sh = c["Sh"]
    Sb = c["Sb"]
    human_friction = (T / 10.0) + 3.0 * (1.0 - Sh)
    bot_risk = B * Sb
    return (1.0 - p) * human_friction + p * bot_risk


def select_best_challenge(
    p: float,
    access_needs: List[str],
    B: float = DEFAULT_BREACH_COST,
    exclude_type: Optional[str] = None,
    filter_accessible: bool = True
) -> Dict[str, Any]:
    """
    Selects optimal challenge c* minimizing J(c).
    Break ties by lower T.
    """
    # Allowed set: C(A) U {none}
    if filter_accessible:
        allowed = get_compatible_challenges(access_needs, exclude_type=exclude_type)
    else:
        allowed = [c for c in CATALOG_CHALLENGES if c["id"] != "none"]
        if exclude_type:
            allowed = [c for c in allowed if c["type"] != exclude_type]

    candidates = [CHALLENGE_MAP["none"]] + allowed

    scored = []
    for c in candidates:
        cost = compute_cost(c, p, B)
        scored.append((cost, c["T"], c["Sb"], c))

    # Sort primarily by cost (ascending), then by T (ascending), then by Sb (ascending)
    scored.sort(key=lambda item: (round(item[0], 6), item[1], item[2]))

    best_item = scored[0]
    best_cost, best_T, best_Sb, best_c = best_item

    # Step up suggested if risk is high (p > 0.5) and chosen Sb > 0.45
    step_up_suggested = bool(p > 0.5 and best_c["Sb"] > 0.45)

    # Top 3 candidate costs for decision trace
    top_3 = [
        {"id": item[3]["id"], "type": item[3]["type"], "cost": round(item[0], 3), "T": item[1], "Sb": item[2]}
        for item in scored[:3]
    ]

    # Categorize band
    if p < 0.15:
        band = "low"
    elif p < 0.65:
        band = "medium"
    else:
        band = "high"

    return {
        "chosen_challenge": best_c,
        "chosen_id": best_c["id"],
        "chosen_type": best_c["type"],
        "band": band,
        "cost": round(best_cost, 4),
        "step_up_suggested": step_up_suggested,
        "allowed_ids": [c["id"] for c in allowed],
        "top_3_candidates": top_3,
        "B": B,
        "p": round(p, 4)
    }


def print_policy_curves():
    p_grid = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.0]
    need_cases = [
        ([], "A={}"),
        (["vision"], "A={vision}"),
        (["vision", "hearing"], "A={vision, hearing}")
    ]

    print("\n--- Policy Curves (Section 2 Tuning Step) ---")
    for needs, label in need_cases:
        row = []
        for p in p_grid:
            res = select_best_challenge(p, needs, B=60.0)
            cid = res["chosen_id"]
            row.append(f"p={p:.2f}:{cid}")
        print(f"{label:25} -> " + " | ".join(row))


if __name__ == "__main__":
    print_policy_curves()

