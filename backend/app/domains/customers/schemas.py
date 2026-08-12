import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.provinces import IRAN_PROVINCES
from app.shared.validation import PHONE_RE

VALID_PROVINCES = set(IRAN_PROVINCES)


class OtpRequestIn(BaseModel):
    phone: str = Field(pattern=PHONE_RE)


class OtpRequestOut(BaseModel):
    sent: bool = True
    # Only populated outside production (cookie_secure=False) so dev/tests can
    # log in without a real SMS gateway. Never returned on a secure deploy.
    dev_code: str | None = None


class OtpVerifyIn(BaseModel):
    phone: str = Field(pattern=PHONE_RE)
    code: str = Field(min_length=4, max_length=8)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    phone: str
    full_name: str | None
    store_name: str | None
    verification_status: str
    verification_documents: list[dict]
    rejection_reason: str | None


class CustomerAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    phone: str
    full_name: str | None
    store_name: str | None
    verification_status: str
    verification_documents: list[dict]
    rejection_reason: str | None
    verified_at: datetime | None
    created_at: datetime


class VerificationUpdate(BaseModel):
    status: str  # "approved" | "rejected"
    reason: str | None = Field(default=None, max_length=300)

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        if v not in ("approved", "rejected"):
            raise ValueError("status must be approved or rejected")
        return v


class CustomerUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=60)
    store_name: str | None = Field(default=None, max_length=80)


class AddressIn(BaseModel):
    title: str = Field(min_length=1, max_length=40)
    province: str
    city: str | None = Field(default=None, max_length=60)
    line: str = Field(min_length=3, max_length=300)
    is_default: bool = False

    @field_validator("province")
    @classmethod
    def province_in_list(cls, v: str) -> str:
        if v not in VALID_PROVINCES:
            raise ValueError("province must be one of the Iran province list")
        return v


class AddressUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=40)
    province: str | None = None
    city: str | None = Field(default=None, max_length=60)
    line: str | None = Field(default=None, min_length=3, max_length=300)
    is_default: bool | None = None

    @field_validator("province")
    @classmethod
    def province_in_list(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_PROVINCES:
            raise ValueError("province must be one of the Iran province list")
        return v


class AddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    province: str
    city: str | None
    line: str
    is_default: bool
