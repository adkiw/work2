from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from uuid import UUID

from . import models, schemas, crud, auth, dependencies
from .database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.post('/auth/login', response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(auth.get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect credentials')
    # assume first tenant of user
    if not user.tenants:
        raise HTTPException(status_code=400, detail='User has no tenant')
    tenant_id = user.tenants[0].tenant_id
    roles = [ut.role.name for ut in user.tenants if ut.tenant_id == tenant_id]
    access_token = auth.create_access_token({'sub': str(user.id), 'tenant_id': str(tenant_id), 'roles': roles})
    refresh_token = auth.create_refresh_token({'sub': str(user.id), 'tenant_id': str(tenant_id), 'roles': roles})
    return {'access_token': access_token, 'refresh_token': refresh_token, 'token_type': 'bearer'}


@app.post('/auth/refresh', response_model=schemas.Token)
def refresh(token: str = Depends(auth.oauth2_scheme)):
    payload = auth.decode_token(token)
    if payload.get('type') != 'refresh':
        raise HTTPException(status_code=400, detail='Invalid refresh token')
    new_access = auth.create_access_token({'sub': payload['sub'], 'tenant_id': payload['tenant_id'], 'roles': payload.get('roles', [])})
    new_refresh = auth.create_refresh_token({'sub': payload['sub'], 'tenant_id': payload['tenant_id'], 'roles': payload.get('roles', [])})
    return {'access_token': new_access, 'refresh_token': new_refresh, 'token_type': 'bearer'}


@app.post('/superadmin/tenants', response_model=schemas.Tenant)
def create_tenant(tenant: schemas.TenantCreate, user_tenant = Depends(dependencies.requires_roles([models.RoleName.SUPERADMIN])), db: Session = Depends(auth.get_db)):
    _, _ = user_tenant
    return crud.create_tenant(db, tenant)


@app.post('/superadmin/tenants/{tenant_id}/admins')
def assign_admin(tenant_id: UUID, email: schemas.UserTenantCreate, user_tenant = Depends(dependencies.requires_roles([models.RoleName.SUPERADMIN])), db: Session = Depends(auth.get_db)):
    user, _ = user_tenant
    db_user = crud.get_user_by_email(db, email.email)
    if not db_user:
        db_user = crud.create_user(db, schemas.UserCreate(email=email.email, password=email.password, full_name=email.full_name))
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail='Tenant not found')
    role = crud.get_role(db, models.RoleName.TENANT_ADMIN)
    crud.add_user_to_tenant(db, db_user, tenant, role)
    return {"detail": "admin assigned"}


@app.post('/{tenant_id}/users', response_model=schemas.User)
def create_user_for_tenant(tenant_id: UUID, user_in: schemas.UserTenantCreate, user_tenant = Depends(dependencies.requires_roles([models.RoleName.TENANT_ADMIN, models.RoleName.SUPERADMIN])), db: Session = Depends(auth.get_db)):
    _, current_tenant_id = user_tenant
    if str(current_tenant_id) != str(tenant_id):
        raise HTTPException(status_code=403, detail='Cross tenant creation forbidden')
    db_user = crud.get_user_by_email(db, user_in.email)
    if db_user:
        raise HTTPException(status_code=400, detail='Email already registered')
    db_user = crud.create_user(db, schemas.UserCreate(email=user_in.email, password=user_in.password, full_name=user_in.full_name))
    role = crud.get_role(db, user_in.role)
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    crud.add_user_to_tenant(db, db_user, tenant, role)
    return db_user


@app.get('/{tenant_id}/shared-data', response_model=list[schemas.Document])
def get_shared_documents(tenant_id: UUID, user_tenant = Depends(dependencies.requires_roles([models.RoleName.USER, models.RoleName.TENANT_ADMIN, models.RoleName.SUPERADMIN])), db: Session = Depends(auth.get_db)):
    _, current_tenant_id = user_tenant
    if str(current_tenant_id) != str(tenant_id):
        raise HTTPException(status_code=403, detail='Forbidden')
    docs = crud.get_shared_documents(db, tenant_id)
    return docs


@app.get('/users/me', response_model=schemas.User)
def read_current_user(user_and_tenant = Depends(dependencies.requires_roles([models.RoleName.USER, models.RoleName.TENANT_ADMIN, models.RoleName.SUPERADMIN]))):
    user, _ = user_and_tenant
    return user
