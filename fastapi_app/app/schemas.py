from typing import List, Optional
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
