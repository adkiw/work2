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
        tenant = models.Tenant(name="t_truck")
        user = models.User(email="truck@example.com", hashed_password=hash_password("pass"), full_name="Truck User")
        assoc = models.UserTenant(user_id=user.id, tenant_id=tenant.id, role_id=role.id)
        db.add_all([tenant, user, assoc])
        db.commit()
        db.refresh(tenant)
        db.refresh(user)
        return user, tenant


def test_create_and_list_trucks():
    user, tenant = setup_user()
    resp = client.post("/auth/login", json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    data = {"numeris": "AAA111", "marke": "MAN", "pagaminimo_metai": 2020}
    r = client.post(f"/{tenant.id}/trucks", json=data, headers=headers)
    assert r.status_code == 200
    tid = r.json()["id"]

    r2 = client.get(f"/{tenant.id}/trucks", headers=headers)
    assert any(t["id"] == tid for t in r2.json())


def test_update_and_delete_truck():
    user, tenant = setup_user()
    login = client.post("/auth/login", json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    truck = {"numeris": "BBB222", "marke": "Volvo"}
    r = client.post(f"/{tenant.id}/trucks", json=truck, headers=headers)
    tid = r.json()["id"]

    upd = {"numeris": "CCC333"}
    r2 = client.put(f"/{tenant.id}/trucks/{tid}", json=upd, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["numeris"] == "CCC333"

    r3 = client.delete(f"/{tenant.id}/trucks/{tid}", headers=headers)
    assert r3.status_code == 204


def test_trailer_swap():
    user, tenant = setup_user()
    login = client.post(
        "/auth/login",
        json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post(f"/{tenant.id}/trailers", json={"numeris": "TR1"}, headers=headers)
    client.post(f"/{tenant.id}/trailers", json={"numeris": "TR2"}, headers=headers)
    client.post(f"/{tenant.id}/trucks", json={"numeris": "AA1"}, headers=headers)
    client.post(
        f"/{tenant.id}/trucks",
        json={"numeris": "BB2", "priekaba": "TR1"},
        headers=headers,
    )

    resp = client.post(
        f"/{tenant.id}/trailer-swap",
        json={"truck_number": "AA1", "trailer_number": "TR1"},
        headers=headers,
    )
    assert resp.status_code == 204

    data = client.get(f"/{tenant.id}/trucks", headers=headers).json()
    trucks = {t["numeris"]: t for t in data}
    assert trucks["AA1"]["priekaba"] == "TR1"
    assert trucks["BB2"]["priekaba"] == ""
