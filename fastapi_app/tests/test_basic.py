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

SQLALCHEMY_DATABASE_URL = 'sqlite:///./test.db'
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={'check_same_thread': False}
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

def test_login_flow():
    with TestingSessionLocal() as db:
        tenant = models.Tenant(name='t1')
        role = models.Role(id=1, name='USER')
        user = models.User(email='user@example.com', hashed_password=hash_password('password'), full_name='User')
        db.add_all([tenant, role, user])
        db.commit()
        assoc = models.UserTenant(user_id=user.id, tenant_id=tenant.id, role_id=role.id)
        db.add(assoc)
        db.commit()
    response = client.post('/auth/login', json={'email': 'user@example.com', 'password': 'password', 'tenant_id': str(tenant.id)})
    assert response.status_code == 200
    tokens = response.json()
    assert 'access_token' in tokens
    assert 'refresh_token' in tokens

    refresh_resp = client.post('/auth/refresh', json={'refresh_token': tokens['refresh_token']})
    assert refresh_resp.status_code == 200
    assert 'access_token' in refresh_resp.json()
