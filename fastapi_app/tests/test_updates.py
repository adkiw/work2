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
        tenant = models.Tenant(name="t_updates")
        user = models.User(email="up@example.com", hashed_password=hash_password("pass"), full_name="Upd User")
        assoc = models.UserTenant(user_id=user.id, tenant_id=tenant.id, role_id=role.id)
        db.add_all([tenant, user, assoc])
        db.commit()
        db.refresh(tenant)
        db.refresh(user)
        return user, tenant


def test_create_and_list_updates():
    user, tenant = setup_user()
    resp = client.post("/auth/login", json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    data = {"vilkiko_numeris": "AAA111", "data": "2025-01-01"}
    r = client.post(f"/{tenant.id}/updates", json=data, headers=headers)
    assert r.status_code == 200
    uid = r.json()["id"]

    r2 = client.get(f"/{tenant.id}/updates", headers=headers)
    assert any(u["id"] == uid for u in r2.json())


def test_update_and_delete_updates():
    user, tenant = setup_user()
    login = client.post("/auth/login", json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    upd = {"vilkiko_numeris": "BBB222", "data": "2025-01-02"}
    r = client.post(f"/{tenant.id}/updates", json=upd, headers=headers)
    uid = r.json()["id"]

    change = upd | {"komentaras": "test"}
    r2 = client.put(f"/{tenant.id}/updates/{uid}", json=change, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["komentaras"] == "test"

    r3 = client.delete(f"/{tenant.id}/updates/{uid}", headers=headers)
    assert r3.status_code == 204


def test_updates_range_and_csv():
    user, tenant = setup_user()
    resp = client.post(
        "/auth/login",
        json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    in_range = {"vilkiko_numeris": "AAA111", "data": "2025-05-01"}
    out_range = {"vilkiko_numeris": "AAA111", "data": "2025-06-01"}
    client.post(f"/{tenant.id}/updates", json=in_range, headers=headers)
    client.post(f"/{tenant.id}/updates", json=out_range, headers=headers)

    r = client.get(
        f"/{tenant.id}/updates-range?start=2025-05-01&end=2025-05-31",
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1

    r_csv = client.get(
        f"/{tenant.id}/updates-range.csv?start=2025-05-01&end=2025-05-31",
        headers=headers,
    )
    assert r_csv.status_code == 200
    assert "attachment" in r_csv.headers.get("content-disposition", "")
