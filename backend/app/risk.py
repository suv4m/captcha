import json
import joblib
import numpy as np
from typing import List, Dict, Any, Union
from backend.app.config import ARTIFACTS_DIR

_CAL_MIN = None
_CAL_FULL = None
_FEATURE_SETS = None


def _load_models():
    global _CAL_MIN, _CAL_FULL, _FEATURE_SETS
    if _CAL_MIN is None:
        _CAL_MIN = joblib.load(ARTIFACTS_DIR / "risk_min.joblib")
    if _CAL_FULL is None:
        _CAL_FULL = joblib.load(ARTIFACTS_DIR / "risk_full.joblib")
    if _FEATURE_SETS is None:
        with open(ARTIFACTS_DIR / "feature_sets.json", "r", encoding="utf-8") as f:
            _FEATURE_SETS = json.load(f)


def get_required_features(mode: str = "min") -> List[str]:
    _load_models()
    if mode == "full":
        return _FEATURE_SETS["full"]["names"]
    return _FEATURE_SETS["min"]["names"]


def score_session_risk(features: Union[List[float], Dict[str, float]], mode: str = "min") -> float:
    _load_models()
    min_indices = _FEATURE_SETS["min"]["indices"]

    if isinstance(features, dict):
        # Dictionary of feature name -> value
        req = get_required_features(mode)
        vec = [float(features.get(name, 0.0)) for name in req]
        X = np.array([vec], dtype=np.float32)
        if mode == "full":
            p = float(_CAL_FULL.predict_proba(X)[0, 1])
        else:
            p = float(_CAL_MIN.predict_proba(X)[0, 1])
    else:
        # List of floats
        vec = [float(v) for v in features]
        if len(vec) == 25:
            # Full vector passed
            X_full = np.array([vec], dtype=np.float32)
            if mode == "full":
                p = float(_CAL_FULL.predict_proba(X_full)[0, 1])
            else:
                X_min = X_full[:, min_indices]
                p = float(_CAL_MIN.predict_proba(X_min)[0, 1])
        elif len(vec) == 8:
            # Min vector passed directly
            X_min = np.array([vec], dtype=np.float32)
            p = float(_CAL_MIN.predict_proba(X_min)[0, 1])
        else:
            # Fallback zero pad
            padded = vec + [0.0] * max(0, 25 - len(vec))
            X_full = np.array([padded[:25]], dtype=np.float32)
            X_min = X_full[:, min_indices]
            p = float(_CAL_MIN.predict_proba(X_min)[0, 1])

    return max(0.0, min(1.0, float(p)))

