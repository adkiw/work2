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

SQLALCHEMY_DATABASE_URL = 'sqlite://'
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={'check_same_thread': False})
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
        role = db.query(models.Role).filter(models.Role.name == 'USER').first()
        if not role:
            role = models.Role(name='USER')
            db.add(role)
            db.commit()
            db.refresh(role)
        tenant = models.Tenant(name='t1')
        user = models.User(email='u@example.com', hashed_password=hash_password('p'), full_name='U')
        assoc = models.UserTenant(user_id=user.id, tenant_id=tenant.id, role_id=role.id)
        db.add_all([tenant, user, assoc])
        db.commit()
        db.refresh(tenant)
        db.refresh(user)
        return user, tenant


def test_create_and_read_audit():
    user, tenant = setup_user()
    resp = client.post('/auth/login', json={'email': user.email, 'password': 'p', 'tenant_id': str(tenant.id)})
    assert resp.status_code == 200
    token = resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    log_data = {
        'action': 'test',
        'table_name': 'doc',
        'record_id': '1',
        'details': {'x': 1}
    }
    r = client.post('/audit', json=log_data, headers=headers)
    assert r.status_code == 200
    created = r.json()
    assert created['action'] == 'test'

    r2 = client.get('/audit', headers=headers)
    assert r2.status_code == 200
    data = r2.json()
    assert any(l['action'] == 'test' for l in data)
