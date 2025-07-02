from sqlalchemy.orm import Session
from uuid import UUID
from . import models, schemas, auth
import json
from datetime import datetime


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    db_user = models.User(
        email=user.email,
        hashed_password=auth.hash_password(user.password),
        full_name=user.full_name,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db: Session, user_id: UUID) -> models.User | None:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()


def create_audit_log(
    db: Session, user_id: UUID | None, data: schemas.AuditLogCreate
) -> models.AuditLog:
    log = models.AuditLog(
        user_id=user_id,
        action=data.action,
        table_name=data.table_name,
        record_id=data.record_id,
        timestamp=datetime.utcnow(),
        details=(
            json.dumps(data.details, ensure_ascii=False)
            if data.details is not None
            else None
        ),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_audit_logs(db: Session, limit: int = 100) -> list[models.AuditLog]:
    return (
        db.query(models.AuditLog)
        .order_by(models.AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )


def create_shipment(
    db: Session, tenant_id: UUID, data: schemas.ShipmentCreate
) -> models.Shipment:
    shipment = models.Shipment(
        tenant_id=tenant_id,
        klientas=data.klientas,
        uzsakymo_numeris=data.uzsakymo_numeris,
        pakrovimo_data=data.pakrovimo_data,
        iskrovimo_data=data.iskrovimo_data,
        kilometrai=data.kilometrai,
        frachtas=data.frachtas,
        busena=data.busena,
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    return shipment


def update_shipment(
    db: Session, tenant_id: UUID, shipment_id: int, data: schemas.ShipmentCreate
) -> models.Shipment | None:
    shipment = (
        db.query(models.Shipment)
        .filter(
            models.Shipment.id == shipment_id,
            models.Shipment.tenant_id == tenant_id,
        )
        .first()
    )
    if not shipment:
        return None
    for field, value in data.dict().items():
        setattr(shipment, field, value)
    db.commit()
    db.refresh(shipment)
    return shipment


def delete_shipment(db: Session, tenant_id: UUID, shipment_id: int) -> bool:
    shipment = (
        db.query(models.Shipment)
        .filter(
            models.Shipment.id == shipment_id,
            models.Shipment.tenant_id == tenant_id,
        )
        .first()
    )
    if not shipment:
        return False
    db.delete(shipment)
    db.commit()
    return True


def get_shipments(db: Session, tenant_id: UUID) -> list[models.Shipment]:
    return (
        db.query(models.Shipment)
        .filter(models.Shipment.tenant_id == tenant_id)
        .order_by(models.Shipment.id.desc())
        .all()
    )
