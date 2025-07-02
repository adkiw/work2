from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from sqlalchemy import or_, and_
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config
import os
from datetime import datetime, timedelta
from uuid import UUID


import pandas as pd

from . import models, schemas, crud, auth, dependencies
from .database import Base
import json

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

FAILED_ATTEMPTS: dict[str, dict] = {}
MAX_FAILURES = 5
LOCK_WINDOW = timedelta(minutes=15)


def _user_locked(email: str) -> bool:
    entry = FAILED_ATTEMPTS.get(email)
    if not entry:
        return False
    locked_until = entry.get("locked_until")
    return locked_until is not None and locked_until > datetime.utcnow()


def _record_failure(email: str) -> None:
    now = datetime.utcnow()
    entry = FAILED_ATTEMPTS.get(email)
    if not entry or now - entry.get("first_fail", now) > LOCK_WINDOW:
        entry = {"count": 1, "first_fail": now}
    else:
        entry["count"] = entry.get("count", 0) + 1
    if entry["count"] >= MAX_FAILURES:
        entry["locked_until"] = now + LOCK_WINDOW
    FAILED_ATTEMPTS[email] = entry


def _clear_failures(email: str) -> None:
    FAILED_ATTEMPTS.pop(email, None)


def run_migrations():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    cfg = Config(os.path.join(base_dir, "alembic.ini"))
    command.upgrade(cfg, "head")


@app.on_event("startup")
def apply_migrations() -> None:
    run_migrations()


@app.post("/login", response_model=schemas.TokenPair)
@limiter.limit("5/minute")
def login(
    data: schemas.LoginRequest, request: Request, db: Session = Depends(auth.get_db)
):
    if _user_locked(data.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts",
        )
    user = auth.authenticate_user(db, data.email, data.password)
    if not user:
        _record_failure(data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials"
        )

    association = (
        db.query(models.UserTenant)
        .filter(
            models.UserTenant.user_id == user.id,
            models.UserTenant.tenant_id == data.tenant_id,
        )
        .first()
    )
    if not association:
        _record_failure(data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant"
        )

    _clear_failures(data.email)
    roles = [association.role.name]
    access_token = auth.create_access_token(str(user.id), str(data.tenant_id), roles)
    refresh_token = auth.create_refresh_token(str(user.id), str(data.tenant_id), roles)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.post("/auth/login", response_model=schemas.TokenPair)
def auth_login(
    data: schemas.LoginRequest, request: Request, db: Session = Depends(auth.get_db)
):
    return login(data, request, db)


@app.post("/auth/refresh", response_model=schemas.Token)
def refresh_token(data: schemas.RefreshRequest):
    payload = auth.verify_refresh_token(data.refresh_token)
    access_token = auth.create_access_token(
        payload["sub"], payload["tenant_id"], payload.get("roles", [])
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/users", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(auth.get_db)):
    db_user = crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db, user)


@app.get("/users/me", response_model=schemas.User)
def read_current_user(current_user=Depends(auth.get_current_user)):
    return current_user


@app.post("/superadmin/tenants", response_model=schemas.Tenant)
def create_tenant(
    tenant: schemas.Tenant,
    current_user=Depends(dependencies.requires_roles(["SUPERADMIN"])),
    db: Session = Depends(auth.get_db),
):
    db_tenant = models.Tenant(name=tenant.name)
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant


@app.post("/superadmin/tenants/{tenant_id}/admins")
def assign_tenant_admin(
    tenant_id: str,
    user_id: str,
    current_user=Depends(dependencies.requires_roles(["SUPERADMIN"])),
    db: Session = Depends(auth.get_db),
):
    role = db.query(models.Role).filter(models.Role.name == "TENANT_ADMIN").first()
    if not role:
        role = models.Role(name="TENANT_ADMIN")
        db.add(role)
        db.commit()
        db.refresh(role)
    assoc = models.UserTenant(user_id=user_id, tenant_id=tenant_id, role_id=role.id)
    db.add(assoc)
    db.commit()
    return {"status": "ok"}


@app.post("/{tenant_id}/users", response_model=schemas.User)
def tenant_create_user(
    tenant_id: str,
    user: schemas.UserCreate,
    current_user=Depends(dependencies.requires_roles(["TENANT_ADMIN"])),
    db: Session = Depends(auth.get_db),
):
    db_user = crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = crud.create_user(db, user)
    role = db.query(models.Role).filter(models.Role.name == "USER").first()
    if not role:
        role = models.Role(name="USER")
        db.add(role)
        db.commit()
        db.refresh(role)
    assoc = models.UserTenant(user_id=new_user.id, tenant_id=tenant_id, role_id=role.id)
    db.add(assoc)
    db.commit()
    return new_user


@app.get("/{tenant_id}/shared-data", response_model=list[schemas.Document])
def read_shared_data(
    tenant_id: str,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    """Return documents for a tenant including its collaborators."""

    current_tenant = str(current_user.current_tenant_id)
    if current_tenant != tenant_id:
        collab_exists = (
            db.query(models.TenantCollaboration)
            .filter(
                or_(
                    and_(
                        models.TenantCollaboration.tenant_a_id == current_tenant,
                        models.TenantCollaboration.tenant_b_id == tenant_id,
                    ),
                    and_(
                        models.TenantCollaboration.tenant_a_id == tenant_id,
                        models.TenantCollaboration.tenant_b_id == current_tenant,
                    ),
                )
            )
            .first()
        )
        if not collab_exists:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

    collaborator_rows = (
        db.query(models.TenantCollaboration)
        .filter(
            or_(
                models.TenantCollaboration.tenant_a_id == tenant_id,
                models.TenantCollaboration.tenant_b_id == tenant_id,
            )
        )
        .all()
    )
    allowed_ids = {tenant_id}
    for row in collaborator_rows:
        allowed_ids.add(str(row.tenant_a_id))
        allowed_ids.add(str(row.tenant_b_id))

    docs = (
        db.query(models.Document)
        .filter(models.Document.tenant_id.in_(allowed_ids))
        .all()
    )
    return docs


@app.post("/{tenant_id}/shipments", response_model=schemas.Shipment)
def create_shipment(
    tenant_id: str,
    shipment: schemas.ShipmentCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    created = crud.create_shipment(db, UUID(tenant_id), shipment)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="create",
            table_name="shipments",
            record_id=str(created.id),
            details=shipment.dict(),
        ),
    )
    return created


@app.get("/{tenant_id}/shipments", response_model=list[schemas.Shipment])
def read_shipments(
    tenant_id: str,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return crud.get_shipments(db, UUID(tenant_id))


@app.put("/{tenant_id}/shipments/{shipment_id}", response_model=schemas.Shipment)
def update_shipment(
    tenant_id: str,
    shipment_id: int,
    shipment: schemas.ShipmentCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    updated = crud.update_shipment(db, UUID(tenant_id), shipment_id, shipment)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="update",
            table_name="shipments",
            record_id=str(shipment_id),
            details=shipment.dict(),
        ),
    )
    return updated


@app.delete("/{tenant_id}/shipments/{shipment_id}", status_code=204)
def delete_shipment(
    tenant_id: str,
    shipment_id: int,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    ok = crud.delete_shipment(db, UUID(tenant_id), shipment_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="delete",
            table_name="shipments",
            record_id=str(shipment_id),
            details=None,
        ),
    )

@app.post("/{tenant_id}/trucks", response_model=schemas.Truck)
def create_truck(
    tenant_id: str,
    truck: schemas.TruckCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    created = crud.create_truck(db, UUID(tenant_id), truck)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="create",
            table_name="trucks",
            record_id=str(created.id),
            details=truck.dict(),
        ),
    )
    return created

@app.get("/{tenant_id}/trucks", response_model=list[schemas.Truck])
def read_trucks(
    tenant_id: str,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return crud.get_trucks(db, UUID(tenant_id))

@app.put("/{tenant_id}/trucks/{truck_id}", response_model=schemas.Truck)
def update_truck(
    tenant_id: str,
    truck_id: int,
    truck: schemas.TruckCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    updated = crud.update_truck(db, UUID(tenant_id), truck_id, truck)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="update",
            table_name="trucks",
            record_id=str(truck_id),
            details=truck.dict(),
        ),
    )
    return updated

@app.delete("/{tenant_id}/trucks/{truck_id}", status_code=204)
def delete_truck(
    tenant_id: str,
    truck_id: int,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    ok = crud.delete_truck(db, UUID(tenant_id), truck_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="delete",
            table_name="trucks",
            record_id=str(truck_id),
            details=None,
        ),
    )
    return Response(status_code=204)


@app.post("/audit", response_model=schemas.AuditLog)
def create_audit_entry(
    log: schemas.AuditLogCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    user_id = current_user.id if current_user else None
    return crud.create_audit_log(db, user_id, log)


@app.get("/audit", response_model=list[schemas.AuditLog])
def read_audit_entries(
    limit: int = 100,
    user_id: UUID | None = None,
    table_name: str | None = None,
    action: str | None = None,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    return crud.get_audit_logs(
        db,
        limit=limit,
        user_id=user_id,
        table_name=table_name,
        action=action,
    )



@app.get("/audit.csv")
def read_audit_csv(
    limit: int = 100,
    user_id: UUID | None = None,
    table_name: str | None = None,
    action: str | None = None,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    logs = crud.get_audit_logs(
        db,
        limit=limit,
        user_id=user_id,
        table_name=table_name,
        action=action,
    )
    df = pd.DataFrame([l.__dict__ for l in logs])
    csv_data = df.to_csv(index=False)
    headers = {"Content-Disposition": "attachment; filename=audit.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)
