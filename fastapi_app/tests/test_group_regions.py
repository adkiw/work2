import os
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
        tenant = models.Tenant(name="t_gr")
        user = models.User(
            email="gr@example.com",
            hashed_password=hash_password("pass"),
            full_name="GroupRegion",
        )
        assoc = models.UserTenant(user_id=user.id, tenant_id=tenant.id, role_id=role.id)
        employee = models.Employee(
            tenant_id=tenant.id,
            vardas="Jonas",
            pavarde="Jonaitis",
        )
        db.add_all([tenant, user, assoc, employee])
        db.commit()
        db.refresh(user)
        db.refresh(tenant)
        db.refresh(employee)
        return user, tenant, employee


def test_group_region_crud():
    user, tenant, emp = setup_user()
    resp = client.post("/auth/login", json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    data = {"numeris": "TR1"}
    r = client.post(f"/{tenant.id}/groups", json=data, headers=headers)
    gid = r.json()["id"]

    reg_data = {"region_code": "LT01", "vadybininkas_id": emp.id}
    r2 = client.post(
        f"/{tenant.id}/groups/{gid}/regions",
        json=reg_data,
        headers=headers,
    )
    assert r2.status_code == 200
    rid = r2.json()["id"]
    assert r2.json()["vadybininkas_id"] == emp.id

    r3 = client.get(f"/{tenant.id}/groups/{gid}/regions", headers=headers)
    assert any(reg["id"] == rid and reg["vadybininkas_id"] == emp.id for reg in r3.json())

    r4 = client.delete(f"/{tenant.id}/group-regions/{rid}", headers=headers)
    assert r4.status_code == 204
    r5 = client.get(f"/{tenant.id}/groups/{gid}/regions", headers=headers)
    assert r5.json() == []


def test_group_regions_csv():
    user, tenant, emp = setup_user()
    resp = client.post(
        "/auth/login",
        json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    grp = client.post(f"/{tenant.id}/groups", json={"numeris": "G1"}, headers=headers)
    gid = grp.json()["id"]
    client.post(
        f"/{tenant.id}/groups/{gid}/regions",
        json={"region_code": "LT01", "vadybininkas_id": emp.id},
        headers=headers,
    )

    r = client.get(f"/{tenant.id}/group-regions.csv", headers=headers)
    assert r.status_code == 200
    header = r.text.splitlines()[0]
    assert "region_code" in header
    assert "vadybininkas_id" in header
    assert "LT01" in r.text
