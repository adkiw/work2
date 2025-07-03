import os
os.environ.setdefault("SECRET_KEY", "test-secret")

from fastapi.testclient import TestClient
from fastapi_app.app.main import app
from fastapi_app.app.auth import get_db, hash_password
from fastapi_app.app.database import Base
from fastapi_app.app import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

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


def _ensure_roles(db):
    roles = {r.name: r for r in db.query(models.Role).all()}
    for name in ["SUPERADMIN", "TENANT_ADMIN", "USER"]:
        if name not in roles:
            role = models.Role(name=name)
            db.add(role)
    db.commit()


def _setup_superadmin(db):
    _ensure_roles(db)
    sa_role = db.query(models.Role).filter(models.Role.name == "SUPERADMIN").first()
    tenant = models.Tenant(name="root")
    user = models.User(
        email="super@example.com",
        hashed_password=hash_password("root"),
        full_name="SA",
        is_active=True,
    )
    assoc = models.UserTenant(user_id=user.id, tenant_id=tenant.id, role_id=sa_role.id)
    db.add_all([tenant, user, assoc])
    db.commit()
    db.refresh(tenant)
    return tenant


def test_active_users_list_and_csv():
    with TestingSessionLocal() as db:
        tenant = _setup_superadmin(db)
        active = models.User(
            email="user@example.com",
            hashed_password=hash_password("x"),
            full_name="User",
            is_active=True,
        )
        role = db.query(models.Role).filter(models.Role.name == "USER").first()
        assoc = models.UserTenant(user_id=active.id, tenant_id=tenant.id, role_id=role.id)
        db.add_all([active, assoc])
        db.commit()

    resp = client.post(
        "/auth/login",
        json={"email": "super@example.com", "password": "root", "tenant_id": str(tenant.id)},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.get("/superadmin/active-users", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert any(u["email"] == "user@example.com" for u in data)

    r_csv = client.get("/superadmin/active-users.csv", headers=headers)
    assert r_csv.status_code == 200
    assert "email" in r_csv.text.splitlines()[0]

