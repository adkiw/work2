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
