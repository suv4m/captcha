import pytest
from ml.extract import extract_features, FEATURE_NAMES

def test_extract_empty_trace():
    trace = {"meta": {"verify_t": 500, "pointer_type": "none"}, "events": []}
    feats = extract_features(trace)
    assert len(feats) == 25
    assert feats[0] == 0.0  # p_n_moves
    assert feats[1] == 0.0  # p_path_len
    assert feats[16] == 500.0  # t_since_mount
    assert feats[17] == 500.0  # t_first_interaction
    assert feats[21] == 0.0  # t_events_total
    assert feats[24] == 1.0  # d_pointer_none

def test_extract_single_event():
    trace = {
        "meta": {"verify_t": 1000, "pointer_type": "mouse"},
        "events": [[120, 0, 10, 20]]
    }
    feats = extract_features(trace)
    assert len(feats) == 25
    assert feats[0] == 1.0  # p_n_moves
    # Motion features 2-10 must be 0 with < 2 pointer moves
    for idx in range(1, 10):
        assert feats[idx] == 0.0
    assert feats[17] == 120.0  # t_first_interaction
    assert feats[21] == 1.0  # t_events_total
    assert feats[22] == 1.0  # d_pointer_mouse

def test_extract_keyboard_assistive_trace():
    # Only keys and focus events, no pointer
    trace = {
        "meta": {"verify_t": 2500, "pointer_type": "none"},
        "events": [
            [200, 5, 0, 0],   # focus
            [500, 2, 0, 0],   # keydown
            [680, 2, 0, 0],   # keydown (dt=180)
            [890, 3, 0, 0],   # backspace (dt=210)
            [1200, 5, 0, 0],  # focus
        ]
    }
    feats = extract_features(trace)
    assert feats[0] == 0.0  # no pointer moves
    assert feats[12] == 3.0  # k_n = 2 keys + 1 backspace
    assert feats[15] == 1.0  # k_backspaces = 1
    assert feats[19] == 0.0  # scrolls
    assert feats[20] == 2.0  # focus changes
    assert feats[24] == 1.0  # d_pointer_none

