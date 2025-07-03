from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPair(Token):
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: UUID


class TokenData(BaseModel):
    user_id: Optional[UUID]
    tenant_id: Optional[UUID]


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: UUID
    is_active: bool = True

    class Config:
        orm_mode = True


class Tenant(BaseModel):
    id: UUID
    name: str

    class Config:
        orm_mode = True


class Role(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True


class Document(BaseModel):
    id: UUID
    tenant_id: UUID
    content: str

    class Config:
        orm_mode = True


class ShipmentBase(BaseModel):
    klientas: str
    uzsakymo_numeris: Optional[str] = None
    pakrovimo_data: Optional[str] = None
    iskrovimo_data: Optional[str] = None
    kilometrai: Optional[int] = 0
    frachtas: Optional[int] = 0
    busena: Optional[str] = None


class ShipmentCreate(ShipmentBase):
    pass


class Shipment(ShipmentBase):
    id: int
    tenant_id: UUID

    class Config:
        orm_mode = True


class AuditLogBase(BaseModel):
    action: str
    table_name: str
    record_id: Optional[str] = None
    details: Optional[dict] = None


class AuditLogCreate(AuditLogBase):
    pass


class AuditLog(AuditLogBase):
    id: int
    user_id: Optional[UUID] = None
    timestamp: datetime

    class Config:
        orm_mode = True

class TruckBase(BaseModel):
    numeris: str
    marke: Optional[str] = None
    pagaminimo_metai: Optional[int] = None
    tech_apziura: Optional[str] = None
    draudimas: Optional[str] = None

class TruckCreate(TruckBase):
    pass

class Truck(TruckBase):
    id: int
    tenant_id: UUID

    class Config:
        orm_mode = True


class DriverBase(BaseModel):
    vardas: str
    pavarde: str
    gimimo_metai: Optional[str] = None
    tautybe: Optional[str] = None
    kadencijos_pabaiga: Optional[str] = None
    atostogu_pabaiga: Optional[str] = None

class DriverCreate(DriverBase):
    pass

class Driver(DriverBase):
    id: int
    tenant_id: UUID

    class Config:
        orm_mode = True


class TrailerBase(BaseModel):
    numeris: str
    priekabu_tipas: Optional[str] = None
    marke: Optional[str] = None
    pagaminimo_metai: Optional[int] = None
    tech_apziura: Optional[str] = None
    draudimas: Optional[str] = None


class TrailerCreate(TrailerBase):
    pass


class Trailer(TrailerBase):
    id: int
    tenant_id: UUID

    class Config:
        orm_mode = True


class TrailerSpecBase(BaseModel):
    tipas: str
    ilgis: Optional[int] = None
    plotis: Optional[int] = None
    aukstis: Optional[int] = None
    keliamoji_galia: Optional[int] = None
    talpa: Optional[int] = None


class TrailerSpecCreate(TrailerSpecBase):
    pass


class TrailerSpec(TrailerSpecBase):
    id: int

    class Config:
        orm_mode = True


class TrailerTypeBase(BaseModel):
    name: str


class TrailerTypeCreate(TrailerTypeBase):
    pass


class TrailerType(TrailerTypeBase):
    id: int

    class Config:
        orm_mode = True


class DefaultTrailerTypes(BaseModel):
    values: list[str]


class ClientBase(BaseModel):
    pavadinimas: str
    vat_numeris: Optional[str] = None
    kontaktinis_asmuo: Optional[str] = None
    kontaktinis_el_pastas: Optional[str] = None
    kontaktinis_tel: Optional[str] = None
    salis: Optional[str] = None
    regionas: Optional[str] = None
    miestas: Optional[str] = None
    adresas: Optional[str] = None
    saskaitos_asmuo: Optional[str] = None
    saskaitos_el_pastas: Optional[str] = None
    saskaitos_tel: Optional[str] = None
    coface_limitas: Optional[float] = 0


class ClientCreate(ClientBase):
    pass


class Client(ClientBase):
    id: int
    tenant_id: UUID

    musu_limitas: Optional[float] = None
    likes_limitas: Optional[float] = None

    class Config:
        orm_mode = True


class GroupBase(BaseModel):
    numeris: str
    pavadinimas: Optional[str] = None
    aprasymas: Optional[str] = None


class GroupCreate(GroupBase):
    pass


class Group(GroupBase):
    id: int
    tenant_id: UUID

    class Config:
        orm_mode = True


class EmployeeBase(BaseModel):
    vardas: str
    pavarde: str
    pareigybe: Optional[str] = None
    el_pastas: Optional[str] = None
    telefonas: Optional[str] = None
    grupe: Optional[str] = None
    aktyvus: Optional[bool] = True


class EmployeeCreate(EmployeeBase):
    pass


class Employee(EmployeeBase):
    id: int
    tenant_id: UUID

    class Config:
        orm_mode = True


class UpdateBase(BaseModel):
    vilkiko_numeris: str
    data: str
    darbo_laikas: Optional[int] = None
    likes_laikas: Optional[int] = None
    pakrovimo_statusas: Optional[str] = None
    pakrovimo_laikas: Optional[str] = None
    pakrovimo_data: Optional[str] = None
    iskrovimo_statusas: Optional[str] = None
    iskrovimo_laikas: Optional[str] = None
    iskrovimo_data: Optional[str] = None
    komentaras: Optional[str] = None
    sa: Optional[str] = None
    created_at: Optional[str] = None
    ats_transporto_vadybininkas: Optional[str] = None
    ats_ekspedicijos_vadybininkas: Optional[str] = None
    trans_grupe: Optional[str] = None
    eksp_grupe: Optional[str] = None


class UpdateCreate(UpdateBase):
    pass


class Update(UpdateBase):
    id: int
    tenant_id: UUID

    class Config:
        orm_mode = True


