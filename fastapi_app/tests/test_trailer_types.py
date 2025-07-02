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
        tenant = models.Tenant(name="t_type")
        user = models.User(email="type@example.com", hashed_password=hash_password("pass"), full_name="Type User")
        assoc = models.UserTenant(user_id=user.id, tenant_id=tenant.id, role_id=role.id)
        db.add_all([tenant, user, assoc])
        db.commit()
        db.refresh(user)
        db.refresh(tenant)
        return user, tenant


def test_trailer_type_defaults():
    user, tenant = setup_user()
    resp = client.post("/auth/login", json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # create trailer type
    data = {"name": "Mega"}
    r = client.post("/trailer-types", json=data, headers=headers)
    assert r.status_code == 200
    t_id = r.json()["id"]

    # list types
    r2 = client.get("/trailer-types", headers=headers)
    assert any(t["id"] == t_id for t in r2.json())

    # update
    upd = {"name": "Jumbo"}
    r3 = client.put(f"/trailer-types/{t_id}", json=upd, headers=headers)
    assert r3.status_code == 200
    assert r3.json()["name"] == "Jumbo"

    # set defaults
    r4 = client.put(f"/{tenant.id}/default-trailer-types", json={"values": ["Jumbo"]}, headers=headers)
    assert r4.status_code == 204

    r5 = client.get(f"/{tenant.id}/default-trailer-types", headers=headers)
    assert r5.json() == ["Jumbo"]

    # delete
    r6 = client.delete(f"/trailer-types/{t_id}", headers=headers)
    assert r6.status_code == 204

