from sqlalchemy import Column, String, Integer, ForeignKey, Table, DateTime, Float
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


class Driver(Base):
    __tablename__ = "drivers"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    vardas = Column(String, nullable=False)
    pavarde = Column(String, nullable=False)
    gimimo_metai = Column(String)
    tautybe = Column(String)
    kadencijos_pabaiga = Column(String)
    atostogu_pabaiga = Column(String)

    tenant = relationship("Tenant")


class Trailer(Base):
    """Priekabos lentelė"""

    __tablename__ = "trailers"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    numeris = Column(String, nullable=False)
    priekabu_tipas = Column(String)
    marke = Column(String)
    pagaminimo_metai = Column(Integer)
    tech_apziura = Column(String)
    draudimas = Column(String)

    tenant = relationship("Tenant")


class TrailerSpec(Base):
    __tablename__ = "trailer_specs"
    id = Column(Integer, primary_key=True)
    tipas = Column(String, unique=True, nullable=False)
    ilgis = Column(Integer)
    plotis = Column(Integer)
    aukstis = Column(Integer)
    keliamoji_galia = Column(Integer)
    talpa = Column(Integer)


class TrailerType(Base):
    """Galimų priekabų tipų sąrašas"""

    __tablename__ = "trailer_types"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class DefaultTrailerType(Base):
    """Įmonės numatytieji priekabų tipai"""

    __tablename__ = "default_trailer_types"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    value = Column(String, nullable=False)
    priority = Column(Integer, nullable=False, default=0)

    tenant = relationship("Tenant")


class Client(Base):
    """Klientų lentelė"""

    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    pavadinimas = Column(String, nullable=False)
    vat_numeris = Column(String)
    kontaktinis_asmuo = Column(String)
    kontaktinis_el_pastas = Column(String)
    kontaktinis_tel = Column(String)
    salis = Column(String)
    regionas = Column(String)
    miestas = Column(String)
    adresas = Column(String)
    saskaitos_asmuo = Column(String)
    saskaitos_el_pastas = Column(String)
    saskaitos_tel = Column(String)
    coface_limitas = Column(Float)
    musu_limitas = Column(Float)
    likes_limitas = Column(Float)

    tenant = relationship("Tenant")


class Group(Base):
    """Darbuotojų ar transporto grupė"""

    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    numeris = Column(String, nullable=False)
    pavadinimas = Column(String)
    aprasymas = Column(String)

    tenant = relationship("Tenant")


class Employee(Base):
    """Darbuotojo įrašas"""

    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    vardas = Column(String, nullable=False)
    pavarde = Column(String, nullable=False)
    pareigybe = Column(String)
    el_pastas = Column(String)
    telefonas = Column(String)
    grupe = Column(String)
    aktyvus = Column(Integer, default=1)

    tenant = relationship("Tenant")


class UpdateEntry(Base):
    """Vilkikų darbo laiko įrašai"""

    __tablename__ = "updates"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    vilkiko_numeris = Column(String, nullable=False)
    data = Column(String, nullable=False)
    darbo_laikas = Column(Integer)
    likes_laikas = Column(Integer)
    pakrovimo_statusas = Column(String)
    pakrovimo_laikas = Column(String)
    pakrovimo_data = Column(String)
    iskrovimo_statusas = Column(String)
    iskrovimo_laikas = Column(String)
    iskrovimo_data = Column(String)
    komentaras = Column(String)
    sa = Column(String)
    created_at = Column(String)
    ats_transporto_vadybininkas = Column(String)
    ats_ekspedicijos_vadybininkas = Column(String)
    trans_grupe = Column(String)
    eksp_grupe = Column(String)

    tenant = relationship("Tenant")

