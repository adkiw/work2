import os
os.environ.setdefault("SECRET_KEY", "test-secret")
from fastapi.testclient import TestClient
from fastapi_app.app.main import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

