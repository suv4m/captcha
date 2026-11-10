import pytest
from ml.extract import extract_features, FEATURE_NAMES

def test_extract_empty_trace():
    trace = {"meta": {"verify_t": 500, "pointer_type": "none"}, "events": []}
    feats = extract_features(trace)
    assert len(feats) == 25
    assert feats[0] == 0.0
    assert feats[1] == 0.0
    assert feats[16] == 500.0
    assert feats[17] == 500.0
    assert feats[21] == 0.0
    assert feats[24] == 1.0

def test_extract_single_event():
    trace = {
        "meta": {"verify_t": 1000, "pointer_type": "mouse"},
        "events": [[120, 0, 10, 20]]
    }
    feats = extract_features(trace)
    assert len(feats) == 25
    assert feats[0] == 1.0

    for idx in range(1, 10):
        assert feats[idx] == 0.0
    assert feats[17] == 120.0
    assert feats[21] == 1.0
    assert feats[22] == 1.0

def test_extract_keyboard_assistive_trace():

    trace = {
        "meta": {"verify_t": 2500, "pointer_type": "none"},
        "events": [
            [200, 5, 0, 0],
            [500, 2, 0, 0],
            [680, 2, 0, 0],
            [890, 3, 0, 0],
            [1200, 5, 0, 0],
        ]
    }
    feats = extract_features(trace)
    assert feats[0] == 0.0
    assert feats[12] == 3.0
    assert feats[15] == 1.0
    assert feats[19] == 0.0
    assert feats[20] == 2.0
    assert feats[24] == 1.0

