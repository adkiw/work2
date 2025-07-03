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
        tenant = models.Tenant(name="t_group")
        user = models.User(email="group@example.com", hashed_password=hash_password("pass"), full_name="Group User")
        assoc = models.UserTenant(user_id=user.id, tenant_id=tenant.id, role_id=role.id)
        db.add_all([tenant, user, assoc])
        db.commit()
        db.refresh(user)
        db.refresh(tenant)
        return user, tenant


def test_crud_groups():
    user, tenant = setup_user()
    resp = client.post("/auth/login", json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    data = {"numeris": "TR1", "pavadinimas": "Test"}
    r = client.post(f"/{tenant.id}/groups", json=data, headers=headers)
    assert r.status_code == 200
    gid = r.json()["id"]

    r2 = client.get(f"/{tenant.id}/groups", headers=headers)
    assert any(g["id"] == gid for g in r2.json())

    upd = {"numeris": "TR2", "pavadinimas": "Upd"}
    r3 = client.put(f"/{tenant.id}/groups/{gid}", json=upd, headers=headers)
    assert r3.status_code == 200
    assert r3.json()["numeris"] == "TR2"

    r4 = client.delete(f"/{tenant.id}/groups/{gid}", headers=headers)
    assert r4.status_code == 204

