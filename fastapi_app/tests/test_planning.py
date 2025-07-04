import os
import datetime
from fastapi.testclient import TestClient
from fastapi_app.app.main import app
from fastapi_app.app.auth import get_db, hash_password
from fastapi_app.app.database import Base
from fastapi_app.app import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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


def setup_user():
    with TestingSessionLocal() as db:
        role = db.query(models.Role).filter(models.Role.name == "USER").first()
        if not role:
            role = models.Role(name="USER")
            db.add(role)
            db.commit()
            db.refresh(role)
        tenant = models.Tenant(name="t_plan")
        user = models.User(email="plan@example.com", hashed_password=hash_password("pass"), full_name="P User")
        assoc = models.UserTenant(user_id=user.id, tenant_id=tenant.id, role_id=role.id)
        db.add_all([tenant, user, assoc])
        db.commit()
        db.refresh(tenant)
        db.refresh(user)
        return user, tenant


def auth_headers(user, tenant):
    resp = client.post(
        "/auth/login",
        json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_planning_endpoints():
    user, tenant = setup_user()
    headers = auth_headers(user, tenant)

    today = datetime.date.today().isoformat()

    client.post(f"/{tenant.id}/trucks", json={"numeris": "AAA111"}, headers=headers)
    shipment = {
        "klientas": "ACME",
        "uzsakymo_numeris": "1",
        "pakrovimo_data": today,
        "iskrovimo_data": today,
        "vilkikas": "AAA111",
    }
    client.post(f"/{tenant.id}/shipments", json=shipment, headers=headers)

    r = client.get(f"/{tenant.id}/planning", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "columns" in data and "data" in data
    assert any(row[data["columns"][0]].startswith("AAA111") for row in data["data"])
    assert today in data["columns"]

    r_csv = client.get(f"/{tenant.id}/planning.csv", headers=headers)
    assert r_csv.status_code == 200
    assert r_csv.headers["content-type"].startswith("text/csv")
    assert "Vilkikas" in r_csv.text.splitlines()[0]
