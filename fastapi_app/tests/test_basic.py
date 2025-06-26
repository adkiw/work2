import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi_app.app.main import app
from fastapi_app.app.database import Base, get_db
from fastapi_app.app import models, crud, schemas

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

# Dependency override

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def create_superadmin(db):
    role = crud.get_role(db, models.RoleName.SUPERADMIN)
    user = crud.create_user(db, schemas.UserCreate(email="admin@example.com", password="secret", full_name="Admin"))
    tenant = crud.create_tenant(db, schemas.TenantCreate(name="acme"))
    crud.add_user_to_tenant(db, user, tenant, role)
    return user, tenant


def test_login_flow():
    db = next(override_get_db())
    user, tenant = create_superadmin(db)
    response = client.post("/auth/login", data={"username": user.email, "password": "secret"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

