import itertools
import pytest
from backend.app.decision import (
    select_best_challenge, get_compatible_challenges, CHALLENGE_MAP
)

ALL_NEEDS = ["vision", "hearing", "motor", "cognitive"]

def all_need_subsets():
    for r in range(len(ALL_NEEDS) + 1):
        for combo in itertools.combinations(ALL_NEEDS, r):
            yield list(combo)

def test_invariant_i3_non_empty_compatible_set():
    """I3: C(A) is non-empty for all 16 need subsets."""
    for needs in all_need_subsets():
        comp = get_compatible_challenges(needs)
        assert len(comp) > 0, f"C(A) is empty for needs: {needs}"

def test_invariant_i1_chosen_is_always_in_compatible_set():
    """I1: c* is always in C(A) U {none}."""
    p_grid = [0.0, 0.05, 0.15, 0.35, 0.65, 0.85, 1.0]
    b_grid = [20.0, 60.0, 100.0, 200.0]

    for needs in all_need_subsets():
        allowed = get_compatible_challenges(needs)
        allowed_ids = {c["id"] for c in allowed} | {"none"}
        for B in b_grid:
            for p in p_grid:
                res = select_best_challenge(p, needs, B=B)
                cid = res["chosen_id"]
                assert cid in allowed_ids, f"I1 violated: {cid} not in allowed set for {needs}"

def test_invariant_i2_strength_never_decreases_as_p_increases():
    """I2: For fixed A and B, challenge strength (lower Sb) never decreases as p increases."""
    p_grid = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.0]
    b_grid = [20.0, 60.0, 120.0, 200.0]

    for needs in all_need_subsets():
        for B in b_grid:
            prev_sb = 1.01
            for p in p_grid:
                res = select_best_challenge(p, needs, B=B)
                curr_sb = res["chosen_challenge"]["Sb"]

                assert curr_sb <= prev_sb + 1e-6, (
                    f"I2 violated: Sb increased from {prev_sb} to {curr_sb} at p={p}, B={B}, needs={needs}"
                )
                prev_sb = curr_sb

def test_invariant_i4_boundary_conditions():
    """I4: At p=0 default B yields none; at p=1 it yields the lowest-Sb allowed entry."""
    for needs in all_need_subsets():

        res_0 = select_best_challenge(0.0, needs, B=60.0)
        assert res_0["chosen_id"] == "none", f"I4 violated at p=0 for needs {needs}: got {res_0['chosen_id']}"

        allowed = get_compatible_challenges(needs)
        min_allowed_sb = min(c["Sb"] for c in allowed)
        res_1 = select_best_challenge(1.0, needs, B=60.0)
        assert abs(res_1["chosen_challenge"]["Sb"] - min_allowed_sb) < 1e-6, (
            f"I4 violated at p=1 for needs {needs}: chosen Sb {res_1['chosen_challenge']['Sb']} != min {min_allowed_sb}"
        )

def test_invariant_i5_raising_b_never_weakens_choice():
    """I5: Raising B never weakens the choice (Sb never increases)."""
    p_grid = [0.05, 0.2, 0.5, 0.8]
    b_sequence = [20.0, 40.0, 60.0, 100.0, 150.0, 200.0]

    for needs in all_need_subsets():
        for p in p_grid:
            prev_sb = 1.01
            for B in b_sequence:
                res = select_best_challenge(p, needs, B=B)
                curr_sb = res["chosen_challenge"]["Sb"]
                assert curr_sb <= prev_sb + 1e-6, (
                    f"I5 violated: Raising B from prev to {B} increased Sb to {curr_sb} for p={p}, needs={needs}"
                )
                prev_sb = curr_sb

