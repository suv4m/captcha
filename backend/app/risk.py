import json
import joblib
import numpy as np
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
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


def score_session_risk(features: Dict[str, float], mode: str = "min") -> float:
    _load_models()

    if not isinstance(features, dict):
        raise HTTPException(status_code=422, detail="features must be a dictionary keyed by feature name")

    req = get_required_features(mode)
    given_keys = set(features.keys())
    req_keys = set(req)

    if given_keys != req_keys:
        missing = list(req_keys - given_keys)
        unknown = list(given_keys - req_keys)
        raise HTTPException(
            status_code=422,
            detail=f"Invalid features: missing={missing}, unknown={unknown}"
        )

    vec = [float(features[name]) for name in req]
    X = np.array([vec], dtype=np.float32)

    if mode == "full":
        p = float(_CAL_FULL.predict_proba(X)[0, 1])
    else:
        p = float(_CAL_MIN.predict_proba(X)[0, 1])

    return max(0.0, min(1.0, float(p)))

