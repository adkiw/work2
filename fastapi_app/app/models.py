from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum

from .database import Base

class Tenant(Base):
    __tablename__ = 'tenants'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    users = relationship('UserTenant', back_populates='tenant')
    collaborations_a = relationship('TenantCollaboration', foreign_keys='TenantCollaboration.tenant_a_id')
    collaborations_b = relationship('TenantCollaboration', foreign_keys='TenantCollaboration.tenant_b_id')

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    failed_login_attempts = Column(Integer, default=0)
    lockout_until = Column(DateTime)
    tenants = relationship('UserTenant', back_populates='user')

class RoleName(str, enum.Enum):
    SUPERADMIN = 'SUPERADMIN'
    TENANT_ADMIN = 'TENANT_ADMIN'
    USER = 'USER'


class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

class UserTenant(Base):
    __tablename__ = 'user_tenants'
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id'))

    user = relationship('User', back_populates='tenants')
    tenant = relationship('Tenant', back_populates='users')
    role = relationship('Role')

class TenantCollaboration(Base):
    __tablename__ = 'tenant_collaborations'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_a_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'))
    tenant_b_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'))


class Document(Base):
    __tablename__ = 'documents'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'))
    content = Column(String)
