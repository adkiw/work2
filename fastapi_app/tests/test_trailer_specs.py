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
        role = db.query(models.Role).filter(models.Role.name == "SUPERADMIN").first()
        if not role:
            role = models.Role(name="SUPERADMIN")
            db.add(role)
            db.commit()
            db.refresh(role)
        tenant = models.Tenant(name="t_spec")
        user = models.User(email="spec@example.com", hashed_password=hash_password("pass"), full_name="Spec User")
        assoc = models.UserTenant(user_id=user.id, tenant_id=tenant.id, role_id=role.id)
        db.add_all([tenant, user, assoc])
        db.commit()
        db.refresh(user)
        db.refresh(tenant)
        return user, tenant


def test_crud_trailer_specs():
    user, tenant = setup_user()
    resp = client.post("/auth/login", json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    data = {"tipas": "TypeA", "ilgis": 13}
    r = client.post("/trailer-specs", json=data, headers=headers)
    assert r.status_code == 200
    spec_id = r.json()["id"]

    r2 = client.get("/trailer-specs", headers=headers)
    assert any(s["id"] == spec_id for s in r2.json())

    upd = {"tipas": "TypeB"}
    r3 = client.put(f"/trailer-specs/{spec_id}", json=upd, headers=headers)
    assert r3.status_code == 200
    assert r3.json()["tipas"] == "TypeB"

    r4 = client.delete(f"/trailer-specs/{spec_id}", headers=headers)
    assert r4.status_code == 204
