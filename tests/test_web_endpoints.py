import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_index_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "adaptive-captcha" in res.text
    assert "Decision Trace" in res.text

def test_widget_static_js(client):
    res = client.get("/widget/adaptive-captcha.js")
    assert res.status_code == 200
    assert "javascript" in res.headers["content-type"]
    assert "AdaptiveCaptcha" in res.text

def test_features_static_js(client):
    res = client.get("/widget/features.js")
    assert res.status_code == 200
    assert "javascript" in res.headers["content-type"]
    assert "extractFeatures" in res.text

def test_styles_static_css(client):
    res = client.get("/static/styles.css")
    assert res.status_code == 200
    assert "css" in res.headers["content-type"]
    assert "--accent" in res.text

