import os
import uuid

os.environ.setdefault("SECRET_KEY", "test-secret")
from fastapi.testclient import TestClient
from fastapi_app.app.main import app
from fastapi_app.app.auth import get_db, hash_password
from fastapi_app.app.database import Base
from fastapi_app.app import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
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
        tenant = models.Tenant(name="s_tenant")
        user = models.User(
            email="ship@example.com",
            hashed_password=hash_password("pass"),
            full_name="Ship User",
        )
        assoc = models.UserTenant(user_id=user.id, tenant_id=tenant.id, role_id=role.id)
        db.add_all([tenant, user, assoc])
        db.commit()
        db.refresh(tenant)
        db.refresh(user)
        return user, tenant


def test_create_and_list_shipments():
    user, tenant = setup_user()
    resp = client.post(
        "/auth/login",
        json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    shipment = {
        "klientas": "ACME",
        "uzsakymo_numeris": "1",
        "pakrovimo_data": "2024-01-01",
        "iskrovimo_data": "2024-01-02",
        "pakrovimo_salis": "LT",
        "pakrovimo_regionas": "02",
        "iskrovimo_salis": "LV",
        "iskrovimo_regionas": "01",
        "vilkikas": "AAA111",
        "kilometrai": 10,
        "frachtas": 20,
        "busena": "Nesuplanuotas",
    }
    r = client.post(f"/{tenant.id}/shipments", json=shipment, headers=headers)
    assert r.status_code == 200
    created = r.json()
    assert created["klientas"] == "ACME"

    r2 = client.get(f"/{tenant.id}/shipments", headers=headers)
    assert r2.status_code == 200
    data = r2.json()
    assert any(s["klientas"] == "ACME" for s in data)


def test_update_and_delete_shipments():
    user, tenant = setup_user()
    login = client.post(
        "/auth/login",
        json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    shipment = {
        "klientas": "ABC",
        "uzsakymo_numeris": "2",
        "pakrovimo_data": "2024-02-01",
        "iskrovimo_data": "2024-02-02",
        "pakrovimo_salis": "LT",
        "pakrovimo_regionas": "02",
        "iskrovimo_salis": "LV",
        "iskrovimo_regionas": "01",
        "vilkikas": "AAA111",
        "kilometrai": 5,
        "frachtas": 10,
        "busena": "Nesuplanuotas",
    }
    r = client.post(f"/{tenant.id}/shipments", json=shipment, headers=headers)
    sid = r.json()["id"]

    update = shipment | {"klientas": "UPDATED"}
    r2 = client.put(
        f"/{tenant.id}/shipments/{sid}", json=update, headers=headers
    )
    assert r2.status_code == 200
    assert r2.json()["klientas"] == "UPDATED"

    r3 = client.delete(
        f"/{tenant.id}/shipments/{sid}", headers=headers
    )
    assert r3.status_code == 204
    r4 = client.get(f"/{tenant.id}/shipments", headers=headers)
    assert all(s["id"] != sid for s in r4.json())
