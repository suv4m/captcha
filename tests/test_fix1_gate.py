import json
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.store import store
from backend.app.risk import get_required_features
from ml.extract import extract_features, FEATURE_NAMES

ROOT_DIR = Path(__file__).resolve().parent.parent
FIXTURES_PATH = ROOT_DIR / "tests" / "fixtures" / "traces.json"

@pytest.fixture
def client():
    return TestClient(app)

def _get_all_js_payloads(fixtures, required_names):
    input_data = [{"trace": item["trace"], "req": required_names} for item in fixtures]
    code = """
    import { buildFeaturePayload } from './widget/features.js';
    import fs from 'node:fs';
    const items = JSON.parse(fs.readFileSync(0, 'utf-8'));
    const results = items.map(x => buildFeaturePayload(x.trace, x.req));
    console.log(JSON.stringify(results));
    """
    res = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        input=json.dumps(input_data),
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True
    )
    if res.returncode != 0:
        raise RuntimeError(f"Node execution failed: {res.stderr}")
    return json.loads(res.stdout)

def test_gate_test_a_js_payload_names_and_order():
    """Test A: for every trace in tests/fixtures/traces.json, the names in the JS payload equal the config names, in the same order as the model expects."""
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    for mode in ["min", "full"]:
        config_names = get_required_features(mode=mode)
        js_payloads = _get_all_js_payloads(fixtures, config_names)
        for item, js_payload in zip(fixtures, js_payloads):
            payload_keys = list(js_payload.keys())
            assert payload_keys == config_names, (
                f"Mismatch in mode {mode} for {item['name']}: {payload_keys} vs {config_names}"
            )

def test_gate_test_b_risk_parity_python_vs_js(client):
    """Test B: for the same traces, /api/session risk computed from the Python extractor equals the risk computed from the JS extractor payload within 1e-6."""
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    for mode in ["min", "full"]:
        policy = "P3" if mode == "min" else "P2"
        config_names = get_required_features(mode=mode)
        js_payloads = _get_all_js_payloads(fixtures, config_names)

        for item, js_payload in zip(fixtures, js_payloads):
            trace = item["trace"]

            py_feats = extract_features(trace)
            py_dict_all = {name: val for name, val in zip(FEATURE_NAMES, py_feats)}
            py_payload = {name: py_dict_all[name] for name in config_names}

            store._seen_features.clear()
            res_py = client.post("/api/session", json={
                "site_key": "test_site",
                "features": py_payload,
                "policy": policy
            })
            assert res_py.status_code == 200, res_py.text
            risk_py = res_py.json()["trace"]["p"]

            store._seen_features.clear()
            res_js = client.post("/api/session", json={
                "site_key": "test_site",
                "features": js_payload,
                "policy": policy
            })
            assert res_js.status_code == 200, res_js.text
            risk_js = res_js.json()["trace"]["p"]

            assert abs(risk_py - risk_js) <= 1e-6, (
                f"Risk mismatch in {mode} for {item['name']}: py={risk_py}, js={risk_js}"
            )

def test_gate_test_c_missing_or_unknown_names_return_422(client):
    """Test C: a payload with wrong or missing names returns 422."""
    config_names = get_required_features(mode="min")

    missing_payload = {k: 1.0 for k in config_names[:-1]}
    res = client.post("/api/session", json={
        "site_key": "test_site",
        "features": missing_payload,
        "policy": "P3"
    })
    assert res.status_code == 422, f"Expected 422 for missing names, got {res.status_code}"

    unknown_payload = {k: 1.0 for k in config_names}
    unknown_payload["extra_unknown_feature"] = 1.0
    res2 = client.post("/api/session", json={
        "site_key": "test_site",
        "features": unknown_payload,
        "policy": "P3"
    })
    assert res2.status_code == 422, f"Expected 422 for unknown names, got {res2.status_code}"

    list_payload = [0.0] * 8
    res3 = client.post("/api/session", json={
        "site_key": "test_site",
        "features": list_payload,
        "policy": "P3"
    })
    assert res3.status_code == 422, f"Expected 422 for list features, got {res3.status_code}"
