import os
os.environ.setdefault("SECRET_KEY", "test-secret")
from fastapi.testclient import TestClient
from fastapi_app.app.main import app
from fastapi_app.app.auth import get_db
from fastapi_app.app.database import Base
from fastapi_app.app import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_roles_list_and_csv():
    with TestingSessionLocal() as db:
        db.add_all([models.Role(name="USER"), models.Role(name="ADMIN")])
        db.commit()

    resp = client.get("/roles")
    assert resp.status_code == 200
    data = resp.json()
    assert any(r["name"] == "USER" for r in data)

    resp_csv = client.get("/roles.csv")
    assert resp_csv.status_code == 200
    assert "name" in resp_csv.text.splitlines()[0]
