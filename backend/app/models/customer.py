import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Customer(Base):
    """A shop customer. Identity is the phone (OTP login). Orders are linked by
    matching phone (they may predate signup), so no FK from orders is required."""

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    phone: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(60))

    addresses: Mapped[list["CustomerAddress"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan", lazy="selectin"
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan", lazy="selectin"
    )


class CustomerAddress(Base):
    __tablename__ = "customer_addresses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. "منزل"
    province: Mapped[str] = mapped_column(String(40), nullable=False)
    city: Mapped[str | None] = mapped_column(String(60))
    line: Mapped[str] = mapped_column(String(300), nullable=False)  # street address
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="addresses")


class Favorite(Base):
    """Wishlist: customer ↔ product. Composite PK prevents dupes."""

    __tablename__ = "favorites"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )

    customer: Mapped["Customer"] = relationship(back_populates="favorites")


class OtpCode(Base):
    """Short-lived login code, hashed at rest. One row per request; verify checks
    the newest unconsumed, unexpired row for the phone."""

    __tablename__ = "otp_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    consumed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
