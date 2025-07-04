import uuid
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


def setup_superadmin():
    with TestingSessionLocal() as db:
        sa_role = db.query(models.Role).filter(models.Role.name == "SUPERADMIN").first()
        user_role = db.query(models.Role).filter(models.Role.name == "USER").first()
        if not sa_role:
            sa_role = models.Role(name="SUPERADMIN")
            db.add(sa_role)
        if not user_role:
            user_role = models.Role(name="USER")
            db.add(user_role)
        tenant = models.Tenant(name="root")
        user = models.User(email="sa@example.com", hashed_password=hash_password("root"), full_name="SA")
        assoc = models.UserTenant(user_id=user.id, tenant_id=tenant.id, role_id=sa_role.id)
        db.add_all([tenant, user, assoc])
        db.commit()
        db.refresh(tenant)
        db.refresh(user)
        return user, tenant


def test_register_and_approve():
    sa_user, tenant = setup_superadmin()
    login = client.post("/auth/login", json={"email": sa_user.email, "password": "root", "tenant_id": str(tenant.id)})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    reg_data = {"email": "new@example.com", "password": "pass", "full_name": "New"}
    r = client.post("/register", json=reg_data, params={"tenant_id": str(tenant.id)})
    assert r.status_code == 201
    new_id = r.json()["user_id"]

    fail = client.post("/auth/login", json={"email": "new@example.com", "password": "pass", "tenant_id": str(tenant.id)})
    assert fail.status_code == 401

    pending = client.get("/superadmin/pending-users", headers=headers)
    assert any(u["id"] == new_id for u in pending.json())

    appr = client.post(f"/superadmin/pending-users/{new_id}/approve", headers=headers)
    assert appr.status_code == 204

    ok = client.post("/auth/login", json={"email": "new@example.com", "password": "pass", "tenant_id": str(tenant.id)})
    assert ok.status_code == 200


def test_pending_users_csv():
    sa_user, tenant = setup_superadmin()
    login = client.post(
        "/auth/login",
        json={"email": sa_user.email, "password": "root", "tenant_id": str(tenant.id)},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    reg_data = {"email": "csv@example.com", "password": "pass", "full_name": "Csv"}
    r = client.post("/register", json=reg_data, params={"tenant_id": str(tenant.id)})
    assert r.status_code == 201

    resp = client.get("/superadmin/pending-users.csv", headers=headers)
    assert resp.status_code == 200
    assert "email" in resp.text.splitlines()[0]
    assert "csv@example.com" in resp.text
