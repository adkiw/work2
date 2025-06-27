from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config
import os


from . import models, schemas, crud, auth, dependencies
from .database import Base

def run_migrations():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    cfg = Config(os.path.join(base_dir, 'alembic.ini'))
    command.upgrade(cfg, 'head')

app = FastAPI()

@app.on_event('startup')
def apply_migrations() -> None:
    run_migrations()

@app.post('/login', response_model=schemas.TokenPair)
def login(data: schemas.LoginRequest, db: Session = Depends(auth.get_db)):
    user = auth.authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect credentials')

    association = (
        db.query(models.UserTenant)
        .filter(models.UserTenant.user_id == user.id, models.UserTenant.tenant_id == data.tenant_id)
        .first()
    )
    if not association:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid tenant')

    roles = [association.role.name]
    access_token = auth.create_access_token(str(user.id), str(data.tenant_id), roles)
    refresh_token = auth.create_refresh_token(str(user.id), str(data.tenant_id), roles)
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer',
    }


@app.post('/auth/login', response_model=schemas.TokenPair)
def auth_login(data: schemas.LoginRequest, db: Session = Depends(auth.get_db)):
    return login(data, db)


@app.post('/auth/refresh', response_model=schemas.Token)
def refresh_token(data: schemas.RefreshRequest):
    payload = auth.verify_refresh_token(data.refresh_token)
    access_token = auth.create_access_token(
        payload['sub'], payload['tenant_id'], payload.get('roles', [])
    )
    return {'access_token': access_token, 'token_type': 'bearer'}

@app.post('/users', response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(auth.get_db)):
    db_user = crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail='Email already registered')
    return crud.create_user(db, user)

@app.get('/users/me', response_model=schemas.User)
def read_current_user(current_user=Depends(auth.get_current_user)):
    return current_user


@app.post('/superadmin/tenants', response_model=schemas.Tenant)
def create_tenant(tenant: schemas.Tenant, current_user=Depends(dependencies.requires_roles(['SUPERADMIN'])), db: Session = Depends(auth.get_db)):
    db_tenant = models.Tenant(name=tenant.name)
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant


@app.post('/superadmin/tenants/{tenant_id}/admins')
def assign_tenant_admin(tenant_id: str, user_id: str, current_user=Depends(dependencies.requires_roles(['SUPERADMIN'])), db: Session = Depends(auth.get_db)):
    role = db.query(models.Role).filter(models.Role.name == 'TENANT_ADMIN').first()
    if not role:
        role = models.Role(name='TENANT_ADMIN')
        db.add(role)
        db.commit()
        db.refresh(role)
    assoc = models.UserTenant(user_id=user_id, tenant_id=tenant_id, role_id=role.id)
    db.add(assoc)
    db.commit()
    return {'status': 'ok'}


@app.post('/{tenant_id}/users', response_model=schemas.User)
def tenant_create_user(tenant_id: str, user: schemas.UserCreate, current_user=Depends(dependencies.requires_roles(['TENANT_ADMIN'])), db: Session = Depends(auth.get_db)):
    db_user = crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail='Email already registered')
    new_user = crud.create_user(db, user)
    role = db.query(models.Role).filter(models.Role.name == 'USER').first()
    if not role:
        role = models.Role(name='USER')
        db.add(role)
        db.commit()
        db.refresh(role)
    assoc = models.UserTenant(user_id=new_user.id, tenant_id=tenant_id, role_id=role.id)
    db.add(assoc)
    db.commit()
    return new_user


@app.get('/{tenant_id}/shared-data', response_model=list[schemas.Document])
def read_shared_data(tenant_id: str, current_user=Depends(auth.get_current_user), db: Session = Depends(auth.get_db)):
    # simplified shared data query without collaborations
    docs = db.query(models.Document).filter(models.Document.tenant_id == tenant_id).all()
    return docs
