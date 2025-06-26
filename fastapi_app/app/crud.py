from sqlalchemy.orm import Session
from uuid import UUID
from . import models, schemas, auth


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


def create_tenant(db: Session, tenant: schemas.TenantCreate) -> models.Tenant:
    db_tenant = models.Tenant(name=tenant.name)
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant


def add_user_to_tenant(db: Session, user: models.User, tenant: models.Tenant, role: models.Role):
    membership = models.UserTenant(user=user, tenant=tenant, role=role)
    db.add(membership)
    db.commit()


def get_role(db: Session, name: models.RoleName) -> models.Role:
    role = db.query(models.Role).filter(models.Role.name == name.value).first()
    if not role:
        role = models.Role(name=name.value)
        db.add(role)
        db.commit()
        db.refresh(role)
    return role


def create_document(db: Session, tenant_id: UUID, content: str) -> models.Document:
    doc = models.Document(tenant_id=tenant_id, content=content)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_documents_for_tenant(db: Session, tenant_id: UUID):
    return db.query(models.Document).filter(models.Document.tenant_id == tenant_id).all()


def get_shared_documents(db: Session, tenant_id: UUID):
    tenant_ids = [tenant_id]
    collaborations = db.query(models.TenantCollaboration).filter(
        (models.TenantCollaboration.tenant_a_id == tenant_id) |
        (models.TenantCollaboration.tenant_b_id == tenant_id)
    ).all()
    for c in collaborations:
        tenant_ids.append(c.tenant_b_id if c.tenant_a_id == tenant_id else c.tenant_a_id)
    return db.query(models.Document).filter(models.Document.tenant_id.in_(tenant_ids)).all()
