from sqlalchemy import Column, String, Integer, ForeignKey, Table, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from .database import Base


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    users = relationship("UserTenant", back_populates="tenant")


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    tenants = relationship("UserTenant", back_populates="user")


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class UserTenant(Base):
    __tablename__ = "user_tenants"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"))

    user = relationship("User", back_populates="tenants")
    tenant = relationship("Tenant", back_populates="users")
    role = relationship("Role")


class TenantCollaboration(Base):
    __tablename__ = "tenant_collaborations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_a_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    tenant_b_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))


class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    content = Column(String, nullable=False)

    tenant = relationship("Tenant")


class Shipment(Base):
    __tablename__ = "shipments"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    klientas = Column(String, nullable=False)
    uzsakymo_numeris = Column(String)
    pakrovimo_data = Column(String)
    iskrovimo_data = Column(String)
    kilometrai = Column(Integer)
    frachtas = Column(Integer)
    busena = Column(String)

    tenant = relationship("Tenant")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    table_name = Column(String, nullable=False)
    record_id = Column(String)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    details = Column(String)

    user = relationship("User")

class Truck(Base):
    __tablename__ = "trucks"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    numeris = Column(String, nullable=False)
    marke = Column(String)
    pagaminimo_metai = Column(Integer)
    tech_apziura = Column(String)
    draudimas = Column(String)

    tenant = relationship("Tenant")
