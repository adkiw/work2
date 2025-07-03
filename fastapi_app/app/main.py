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
from modules.constants import EU_COUNTRIES

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


@app.post("/register", status_code=201)
def register_user(
    data: schemas.UserCreate,
    tenant_id: UUID,
    db: Session = Depends(auth.get_db),
):
    """Sukurti neaktyvų vartotoją ir priskirti jį tenantui."""
    db_user = crud.get_user_by_email(db, data.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = crud.create_user(db, data, active=False)
    role = db.query(models.Role).filter(models.Role.name == "USER").first()
    if not role:
        role = models.Role(name="USER")
        db.add(role)
        db.commit()
        db.refresh(role)
    assoc = models.UserTenant(user_id=user.id, tenant_id=tenant_id, role_id=role.id)
    db.add(assoc)
    db.commit()
    return {"user_id": str(user.id)}


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


@app.get("/superadmin/pending-users", response_model=list[schemas.User])
def list_pending_users(
    current_user=Depends(dependencies.requires_roles(["SUPERADMIN"])),
    db: Session = Depends(auth.get_db),
):
    return db.query(models.User).filter(models.User.is_active == False).all()


@app.post("/superadmin/pending-users/{user_id}/approve", status_code=204)
def approve_pending_user(
    user_id: str,
    current_user=Depends(dependencies.requires_roles(["SUPERADMIN"])),
    db: Session = Depends(auth.get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user.is_active = True
    db.commit()
    return Response(status_code=204)


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


@app.post("/{tenant_id}/drivers", response_model=schemas.Driver)
def create_driver(
    tenant_id: str,
    driver: schemas.DriverCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    created = crud.create_driver(db, UUID(tenant_id), driver)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="create",
            table_name="drivers",
            record_id=str(created.id),
            details=driver.dict(),
        ),
    )
    return created


@app.get("/{tenant_id}/drivers", response_model=list[schemas.Driver])
def read_drivers(
    tenant_id: str,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return crud.get_drivers(db, UUID(tenant_id))


@app.put("/{tenant_id}/drivers/{driver_id}", response_model=schemas.Driver)
def update_driver(
    tenant_id: str,
    driver_id: int,
    driver: schemas.DriverCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    updated = crud.update_driver(db, UUID(tenant_id), driver_id, driver)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="update",
            table_name="drivers",
            record_id=str(driver_id),
            details=driver.dict(),
        ),
    )
    return updated


@app.delete("/{tenant_id}/drivers/{driver_id}", status_code=204)
def delete_driver(
    tenant_id: str,
    driver_id: int,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    ok = crud.delete_driver(db, UUID(tenant_id), driver_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="delete",
            table_name="drivers",
            record_id=str(driver_id),
            details=None,
        ),
    )
    return Response(status_code=204)


@app.post("/{tenant_id}/trailers", response_model=schemas.Trailer)
def create_trailer(
    tenant_id: str,
    trailer: schemas.TrailerCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    created = crud.create_trailer(db, UUID(tenant_id), trailer)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="create",
            table_name="trailers",
            record_id=str(created.id),
            details=trailer.dict(),
        ),
    )
    return created


@app.get("/{tenant_id}/trailers", response_model=list[schemas.Trailer])
def read_trailers(
    tenant_id: str,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return crud.get_trailers(db, UUID(tenant_id))


@app.put("/{tenant_id}/trailers/{trailer_id}", response_model=schemas.Trailer)
def update_trailer(
    tenant_id: str,
    trailer_id: int,
    trailer: schemas.TrailerCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    updated = crud.update_trailer(db, UUID(tenant_id), trailer_id, trailer)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="update",
            table_name="trailers",
            record_id=str(trailer_id),
            details=trailer.dict(),
        ),
    )
    return updated


@app.delete("/{tenant_id}/trailers/{trailer_id}", status_code=204)
def delete_trailer(
    tenant_id: str,
    trailer_id: int,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    ok = crud.delete_trailer(db, UUID(tenant_id), trailer_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="delete",
            table_name="trailers",
            record_id=str(trailer_id),
            details=None,
        ),
    )
    return Response(status_code=204)


@app.post("/trailer-specs", response_model=schemas.TrailerSpec)
def create_trailer_spec(
    spec: schemas.TrailerSpecCreate,
    current_user=Depends(dependencies.requires_roles(["SUPERADMIN"])),
    db: Session = Depends(auth.get_db),
):
    created = crud.create_trailer_spec(db, spec)
    return created


@app.get("/trailer-specs", response_model=list[schemas.TrailerSpec])
def read_trailer_specs(
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    return crud.get_trailer_specs(db)


@app.put("/trailer-specs/{spec_id}", response_model=schemas.TrailerSpec)
def update_trailer_spec(
    spec_id: int,
    spec: schemas.TrailerSpecCreate,
    current_user=Depends(dependencies.requires_roles(["SUPERADMIN"])),
    db: Session = Depends(auth.get_db),
):
    updated = crud.update_trailer_spec(db, spec_id, spec)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return updated


@app.delete("/trailer-specs/{spec_id}", status_code=204)
def delete_trailer_spec(
    spec_id: int,
    current_user=Depends(dependencies.requires_roles(["SUPERADMIN"])),
    db: Session = Depends(auth.get_db),
):
    ok = crud.delete_trailer_spec(db, spec_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(status_code=204)


@app.post("/trailer-types", response_model=schemas.TrailerType)
def create_trailer_type(
    tt: schemas.TrailerTypeCreate,
    current_user=Depends(dependencies.requires_roles(["SUPERADMIN"])),
    db: Session = Depends(auth.get_db),
):
    return crud.create_trailer_type(db, tt)


@app.get("/trailer-types", response_model=list[schemas.TrailerType])
def read_trailer_types(
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    return crud.get_trailer_types(db)


@app.put("/trailer-types/{type_id}", response_model=schemas.TrailerType)
def update_trailer_type(
    type_id: int,
    tt: schemas.TrailerTypeCreate,
    current_user=Depends(dependencies.requires_roles(["SUPERADMIN"])),
    db: Session = Depends(auth.get_db),
):
    updated = crud.update_trailer_type(db, type_id, tt)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return updated


@app.delete("/trailer-types/{type_id}", status_code=204)
def delete_trailer_type(
    type_id: int,
    current_user=Depends(dependencies.requires_roles(["SUPERADMIN"])),
    db: Session = Depends(auth.get_db),
):
    ok = crud.delete_trailer_type(db, type_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(status_code=204)


@app.get("/{tenant_id}/default-trailer-types", response_model=list[str])
def get_default_trailer_types_api(
    tenant_id: str,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return crud.get_default_trailer_types(db, UUID(tenant_id))


@app.put("/{tenant_id}/default-trailer-types", status_code=204)
def set_default_trailer_types_api(
    tenant_id: str,
    data: schemas.DefaultTrailerTypes,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    crud.set_default_trailer_types(db, UUID(tenant_id), data.values)
    return Response(status_code=204)


@app.post("/{tenant_id}/clients", response_model=schemas.Client)
def create_client_api(
    tenant_id: str,
    client: schemas.ClientCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    created = crud.create_client(db, UUID(tenant_id), client)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="create",
            table_name="clients",
            record_id=str(created.id),
            details=client.dict(),
        ),
    )
    return created


@app.get("/{tenant_id}/clients", response_model=list[schemas.Client])
def read_clients_api(
    tenant_id: str,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return crud.get_clients(db, UUID(tenant_id))


@app.put("/{tenant_id}/clients/{client_id}", response_model=schemas.Client)
def update_client_api(
    tenant_id: str,
    client_id: int,
    client: schemas.ClientCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    updated = crud.update_client(db, UUID(tenant_id), client_id, client)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="update",
            table_name="clients",
            record_id=str(client_id),
            details=client.dict(),
        ),
    )
    return updated


@app.delete("/{tenant_id}/clients/{client_id}", status_code=204)
def delete_client_api(
    tenant_id: str,
    client_id: int,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    ok = crud.delete_client(db, UUID(tenant_id), client_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="delete",
            table_name="clients",
            record_id=str(client_id),
            details=None,
        ),
    )
    return Response(status_code=204)


@app.post("/{tenant_id}/groups", response_model=schemas.Group)
def create_group_api(
    tenant_id: str,
    group: schemas.GroupCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    created = crud.create_group(db, UUID(tenant_id), group)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="create",
            table_name="groups",
            record_id=str(created.id),
            details=group.dict(),
        ),
    )
    return created


@app.get("/{tenant_id}/groups", response_model=list[schemas.Group])
def read_groups_api(
    tenant_id: str,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return crud.get_groups(db, UUID(tenant_id))


@app.put("/{tenant_id}/groups/{group_id}", response_model=schemas.Group)
def update_group_api(
    tenant_id: str,
    group_id: int,
    group: schemas.GroupCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    updated = crud.update_group(db, UUID(tenant_id), group_id, group)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="update",
            table_name="groups",
            record_id=str(group_id),
            details=group.dict(),
        ),
    )
    return updated


@app.delete("/{tenant_id}/groups/{group_id}", status_code=204)
def delete_group_api(
    tenant_id: str,
    group_id: int,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    ok = crud.delete_group(db, UUID(tenant_id), group_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="delete",
            table_name="groups",
            record_id=str(group_id),
            details=None,
        ),
    )
    return Response(status_code=204)


@app.post("/{tenant_id}/employees", response_model=schemas.Employee)
def create_employee_api(
    tenant_id: str,
    emp: schemas.EmployeeCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    created = crud.create_employee(db, UUID(tenant_id), emp)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="create",
            table_name="employees",
            record_id=str(created.id),
            details=emp.dict(),
        ),
    )
    return created


@app.get("/{tenant_id}/employees", response_model=list[schemas.Employee])
def read_employees_api(
    tenant_id: str,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return crud.get_employees(db, UUID(tenant_id))


@app.put("/{tenant_id}/employees/{emp_id}", response_model=schemas.Employee)
def update_employee_api(
    tenant_id: str,
    emp_id: int,
    emp: schemas.EmployeeCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    updated = crud.update_employee(db, UUID(tenant_id), emp_id, emp)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="update",
            table_name="employees",
            record_id=str(emp_id),
            details=emp.dict(),
        ),
    )
    return updated


@app.delete("/{tenant_id}/employees/{emp_id}", status_code=204)
def delete_employee_api(
    tenant_id: str,
    emp_id: int,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    ok = crud.delete_employee(db, UUID(tenant_id), emp_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="delete",
            table_name="employees",
            record_id=str(emp_id),
            details=None,
        ),
    )
    return Response(status_code=204)


@app.post("/{tenant_id}/updates", response_model=schemas.Update)
def create_update_api(
    tenant_id: str,
    update: schemas.UpdateCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    created = crud.create_update(db, UUID(tenant_id), update)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="create",
            table_name="updates",
            record_id=str(created.id),
            details=update.dict(),
        ),
    )
    return created


@app.get("/{tenant_id}/updates", response_model=list[schemas.Update])
def read_updates_api(
    tenant_id: str,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return crud.get_updates(db, UUID(tenant_id))


@app.put("/{tenant_id}/updates/{update_id}", response_model=schemas.Update)
def update_update_api(
    tenant_id: str,
    update_id: int,
    update: schemas.UpdateCreate,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    updated = crud.update_update(db, UUID(tenant_id), update_id, update)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="update",
            table_name="updates",
            record_id=str(update_id),
            details=update.dict(),
        ),
    )
    return updated


@app.delete("/{tenant_id}/updates/{update_id}", status_code=204)
def delete_update_api(
    tenant_id: str,
    update_id: int,
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db),
):
    if str(current_user.current_tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    ok = crud.delete_update(db, UUID(tenant_id), update_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    crud.create_audit_log(
        db,
        current_user.id,
        schemas.AuditLogCreate(
            action="delete",
            table_name="updates",
            record_id=str(update_id),
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


@app.get("/eu-countries")
def eu_countries_api():
    """Grąžina Europos šalių sąrašą."""
    return {
        "data": [{"name": name, "code": code} for name, code in EU_COUNTRIES if name]
    }
