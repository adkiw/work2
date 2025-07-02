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


def create_audit_log(db: Session, user_id: UUID | None, data: schemas.AuditLogCreate) -> models.AuditLog:
    log = models.AuditLog(
        user_id=user_id,
        action=data.action,
        table_name=data.table_name,
        record_id=data.record_id,
        timestamp=datetime.utcnow(),
        details=json.dumps(data.details, ensure_ascii=False) if data.details is not None else None,
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
