import uuid
from fastapi.testclient import TestClient
from fastapi_app.app.main import app
from fastapi_app.app.auth import get_db, hash_password
from fastapi_app.app.database import Base
from fastapi_app.app import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = 'sqlite:///./test.db'
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


def test_shared_data_with_collaboration():
    with TestingSessionLocal() as db:
        t1 = models.Tenant(name='collab_t1')
        t2 = models.Tenant(name='collab_t2')
        role = db.query(models.Role).filter(models.Role.name == 'USER').first()
        if not role:
            role = models.Role(id=1, name='USER')
            db.add(role)
        user = models.User(email='collab_user@example.com', hashed_password=hash_password('pass'), full_name='User')
        assoc = models.UserTenant(user_id=user.id, tenant_id=t1.id, role_id=role.id)
        doc1 = models.Document(tenant_id=t1.id, content='doc1')
        doc2 = models.Document(tenant_id=t2.id, content='doc2')
        collab = models.TenantCollaboration(tenant_a_id=t1.id, tenant_b_id=t2.id)
        db.add_all([t1, t2, user, assoc, doc1, doc2, collab])
        db.commit()
        db.refresh(t1)
        db.refresh(t2)

    resp = client.post('/auth/login', json={'email': 'collab_user@example.com', 'password': 'pass', 'tenant_id': str(t1.id)})
    assert resp.status_code == 200
    tokens = resp.json()
    headers = {'Authorization': f"Bearer {tokens['access_token']}"}

    r1 = client.get(f'/{t1.id}/shared-data', headers=headers)
    assert r1.status_code == 200
    data1 = r1.json()
    assert {str(d['tenant_id']) for d in data1} == {str(t1.id), str(t2.id)}

    r2 = client.get(f'/{t2.id}/shared-data', headers=headers)
    assert r2.status_code == 200
    data2 = r2.json()
    assert {str(d['tenant_id']) for d in data2} == {str(t1.id), str(t2.id)}


def test_shared_data_without_collaboration():
    with TestingSessionLocal() as db:
        t1 = models.Tenant(name='nocollab_t1')
        t3 = models.Tenant(name='nocollab_t3')
        role = db.query(models.Role).filter(models.Role.name == 'USER').first()
        if not role:
            role = models.Role(id=1, name='USER')
            db.add(role)
        user = models.User(email='nocollab_user@example.com', hashed_password=hash_password('pass2'), full_name='User')
        assoc = models.UserTenant(user_id=user.id, tenant_id=t1.id, role_id=role.id)
        doc = models.Document(tenant_id=t3.id, content='doc3')
        db.add_all([t1, t3, user, assoc, doc])
        db.commit()
        db.refresh(t1)
        db.refresh(t3)

    resp = client.post('/auth/login', json={'email': 'nocollab_user@example.com', 'password': 'pass2', 'tenant_id': str(t1.id)})
    assert resp.status_code == 200
    tokens = resp.json()
    headers = {'Authorization': f"Bearer {tokens['access_token']}"}

    r = client.get(f'/{t3.id}/shared-data', headers=headers)
    assert r.status_code == 403

