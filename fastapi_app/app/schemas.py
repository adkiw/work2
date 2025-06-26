from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from .models import RoleName

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None

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

class TenantCreate(BaseModel):
    name: str


class UserTenantCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: RoleName

class Role(BaseModel):
    id: int
    name: RoleName

    class Config:
        orm_mode = True


class Document(BaseModel):
    id: UUID
    tenant_id: UUID
    content: str

    class Config:
        orm_mode = True
