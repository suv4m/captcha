import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_lab_page_loads(client):
    res = client.get("/lab")
    assert res.status_code == 200
    assert "Policy Benchmark" in res.text
    assert "Interactive Policy Simulation" in res.text


def test_lab_results_endpoint(client):
    res = client.get("/api/lab/results")
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert "metrics" in data

    # Verify policy table plausibility
    p0 = data["results"]["P0"]
    p3 = data["results"]["P3"]

    # P0 should have accessibility violations (approx 6%)
    assert p0["a11y_violation_rate"]["mean"] > 0.04
    # P3 must have 0.00% accessibility violations
    assert p3["a11y_violation_rate"]["mean"] == 0.0
    # P3 human pass rate must meet or exceed P0, with zero accessibility violations and lower time
    assert p3["human_pass_rate"]["mean"] >= p0["human_pass_rate"]["mean"]
    assert p3["mean_human_time_s"]["mean"] < p0["mean_human_time_s"]["mean"]
    assert 0.0 <= p3["security_rate"]["mean"] <= 1.0


def test_lab_simulate_endpoint(client):
    # Vectorized fast simulation (<100ms)
    res = client.get("/api/lab/simulate?policy=P3&breach_cost=80&runs=10")
    assert res.status_code == 200
    sim = res.json()
    assert sim["policy"] == "P3"
    assert sim["breach_cost"] == 80.0
    assert 0.0 <= sim["security_rate"] <= 1.0
    assert 0.0 <= sim["human_pass_rate"] <= 1.0
    assert sim["a11y_violation_rate"] == 0.0

