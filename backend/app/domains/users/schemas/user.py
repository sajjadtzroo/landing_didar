import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domains.users.models import AdminRole


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=60, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, max_length=20)
    role: AdminRole


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, max_length=20)
    role: AdminRole | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    username: str
    full_name: str | None
    phone: str | None
    role: AdminRole
    is_active: bool
    created_at: datetime


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    actor: str
    action: str
    status: int | None
    created_at: datetime


class AuditListOut(BaseModel):
    items: list[AuditOut]
    total: int
    page: int
    page_size: int
