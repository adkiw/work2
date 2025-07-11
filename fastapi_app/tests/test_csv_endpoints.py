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
        tenant = models.Tenant(name="t_csv")
        user = models.User(
            email="csv@example.com",
            hashed_password=hash_password("pass"),
            full_name="CSV User",
        )
        assoc = models.UserTenant(user_id=user.id, tenant_id=tenant.id, role_id=role.id)
        db.add_all([tenant, user, assoc])
        db.commit()
        db.refresh(user)
        db.refresh(tenant)
        return user, tenant


def auth_headers(user, tenant):
    resp = client.post(
        "/auth/login",
        json={"email": user.email, "password": "pass", "tenant_id": str(tenant.id)},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_csv_exports():
    user, tenant = setup_user()
    headers = auth_headers(user, tenant)

    # create sample records
    client.post(
        f"/{tenant.id}/shipments",
        json={"klientas": "A", "uzsakymo_numeris": "1"},
        headers=headers,
    )
    client.post(f"/{tenant.id}/trucks", json={"numeris": "AAA111"}, headers=headers)
    client.post(
        f"/{tenant.id}/drivers",
        json={"vardas": "Jonas", "pavarde": "Jonaitis"},
        headers=headers,
    )
    client.post(f"/{tenant.id}/trailers", json={"numeris": "TR123"}, headers=headers)
    client.post(f"/{tenant.id}/clients", json={"pavadinimas": "ACME"}, headers=headers)
    client.post(f"/{tenant.id}/groups", json={"numeris": "G1"}, headers=headers)
    client.post(f"/{tenant.id}/employees", json={"vardas": "E", "pavarde": "V"}, headers=headers)
    client.post(
        f"/{tenant.id}/updates",
        json={"vilkiko_numeris": "AAA111", "data": "2023-01-01"},
        headers=headers,
    )

    with TestingSessionLocal() as db:
        db.add(models.TrailerSpec(tipas="Mega"))
        db.add(models.TrailerType(name="Type1"))
        db.commit()

    r1 = client.get(f"/{tenant.id}/shipments.csv", headers=headers)
    assert r1.status_code == 200
    assert "klientas" in r1.text.splitlines()[0]

    r2 = client.get(f"/{tenant.id}/trucks.csv", headers=headers)
    assert r2.status_code == 200
    assert "numeris" in r2.text.splitlines()[0]

    r3 = client.get(f"/{tenant.id}/drivers.csv", headers=headers)
    assert r3.status_code == 200
    assert "vardas" in r3.text.splitlines()[0]

    r4 = client.get(f"/{tenant.id}/trailers.csv", headers=headers)
    assert r4.status_code == 200
    assert "numeris" in r4.text.splitlines()[0]

    r5 = client.get(f"/{tenant.id}/clients.csv", headers=headers)
    assert r5.status_code == 200
    assert "pavadinimas" in r5.text.splitlines()[0]

    r6 = client.get(f"/{tenant.id}/groups.csv", headers=headers)
    assert r6.status_code == 200
    assert "numeris" in r6.text.splitlines()[0]

    r7 = client.get(f"/{tenant.id}/employees.csv", headers=headers)
    assert r7.status_code == 200
    assert "vardas" in r7.text.splitlines()[0]

    r8 = client.get(f"/{tenant.id}/updates.csv", headers=headers)
    assert r8.status_code == 200
    assert "vilkiko_numeris" in r8.text.splitlines()[0]

    r9 = client.get("/trailer-specs.csv", headers=headers)
    assert r9.status_code == 200
    assert "tipas" in r9.text.splitlines()[0]

    r10 = client.get("/trailer-types.csv", headers=headers)
    assert r10.status_code == 200
    assert "name" in r10.text.splitlines()[0]
