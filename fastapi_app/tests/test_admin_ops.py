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


def _ensure_roles(db):
    roles = {r.name: r for r in db.query(models.Role).all()}
    for name in ["SUPERADMIN", "TENANT_ADMIN", "USER"]:
        if name not in roles:
            role = models.Role(name=name)
            db.add(role)
    db.commit()


def test_tenant_isolation():
    with TestingSessionLocal() as db:
        _ensure_roles(db)
        t1 = models.Tenant(name="iso_t1")
        t2 = models.Tenant(name="iso_t2")
        user_role = db.query(models.Role).filter(models.Role.name == "USER").first()
        user = models.User(email="iso@example.com", hashed_password=hash_password("pass"), full_name="Iso")
        assoc = models.UserTenant(user_id=user.id, tenant_id=t1.id, role_id=user_role.id)
        doc1 = models.Document(tenant_id=t1.id, content="d1")
        doc2 = models.Document(tenant_id=t2.id, content="d2")
        db.add_all([t1, t2, user, assoc, doc1, doc2])
        db.commit()
        db.refresh(t1)
        db.refresh(t2)

    resp = client.post('/auth/login', json={'email': 'iso@example.com', 'password': 'pass', 'tenant_id': str(t1.id)})
    assert resp.status_code == 200
    token = resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    r = client.get(f'/{t2.id}/shared-data', headers=headers)
    assert r.status_code == 403


def test_rls_policy_blocks_queries():
    with TestingSessionLocal() as db:
        _ensure_roles(db)
        t1 = models.Tenant(name="rls_t1")
        t2 = models.Tenant(name="rls_t2")
        role = db.query(models.Role).filter(models.Role.name == "USER").first()
        user = models.User(email="rls@example.com", hashed_password=hash_password("pass"), full_name="Rls")
        assoc = models.UserTenant(user_id=user.id, tenant_id=t1.id, role_id=role.id)
        doc1 = models.Document(tenant_id=t1.id, content="allowed")
        doc2 = models.Document(tenant_id=t2.id, content="forbidden")
        db.add_all([t1, t2, user, assoc, doc1, doc2])
        db.commit()
        db.refresh(t1)

    resp = client.post('/auth/login', json={'email': 'rls@example.com', 'password': 'pass', 'tenant_id': str(t1.id)})
    assert resp.status_code == 200
    token = resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    r = client.get(f'/{t1.id}/shared-data', headers=headers)
    assert r.status_code == 200
    data = r.json()
    ids = {str(d['tenant_id']) for d in data}
    assert str(t1.id) in ids
    assert str(t2.id) not in ids


def test_superadmin_workflow():
    with TestingSessionLocal() as db:
        _ensure_roles(db)
        sa_role = db.query(models.Role).filter(models.Role.name == "SUPERADMIN").first()
        root_tenant = models.Tenant(name="root")
        sa_user = models.User(email="super@example.com", hashed_password=hash_password("root"), full_name="SA")
        assoc = models.UserTenant(user_id=sa_user.id, tenant_id=root_tenant.id, role_id=sa_role.id)
        db.add_all([root_tenant, sa_user, assoc])
        db.commit()
        db.refresh(root_tenant)

    login_resp = client.post('/auth/login', json={'email': 'super@example.com', 'password': 'root', 'tenant_id': str(root_tenant.id)})
    assert login_resp.status_code == 200
    token = login_resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    new_tenant_id = str(uuid.uuid4())
    r = client.post('/superadmin/tenants', json={'id': new_tenant_id, 'name': 'newtenant'}, headers=headers)
    assert r.status_code == 200
    tenant_resp = r.json()

    admin_data = {'email': 'admin@example.com', 'password': 'pass', 'full_name': 'Admin'}
    create_admin = client.post('/users', json=admin_data)
    assert create_admin.status_code == 200
    admin_user = create_admin.json()

    assign = client.post(f"/superadmin/tenants/{tenant_resp['id']}/admins", params={'user_id': admin_user['id']}, headers=headers)
    assert assign.status_code == 200

    login_admin = client.post('/auth/login', json={'email': admin_data['email'], 'password': admin_data['password'], 'tenant_id': tenant_resp['id']})
    assert login_admin.status_code == 200
    admin_token = login_admin.json()['access_token']
    admin_headers = {'Authorization': f'Bearer {admin_token}'}

    new_user_data = {'email': 'tenantuser@example.com', 'password': 'pass', 'full_name': 'Tenant User'}
    r_user = client.post(f"/{tenant_resp['id']}/users", headers=admin_headers, json=new_user_data)
    assert r_user.status_code == 200
