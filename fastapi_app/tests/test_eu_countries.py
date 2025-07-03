import os
os.environ.setdefault("SECRET_KEY", "test-secret")
from fastapi.testclient import TestClient
from fastapi_app.app.main import app

client = TestClient(app)


def test_eu_countries_endpoint():
    resp = client.get("/eu-countries")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert any(c["code"] == "LT" for c in data)


def test_eu_countries_csv():
    resp = client.get("/eu-countries.csv")
    assert resp.status_code == 200
    assert "code" in resp.text.splitlines()[0]
