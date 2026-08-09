import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class OrderStatus(enum.StrEnum):
    """WO 7.4 mapping: new≈Submitted, confirmed≈Approved, shipped≈Dispatched."""

    new = "new"
    contacted = "contacted"
    confirmed = "confirmed"
    preparing = "preparing"  # در حال آماده‌سازی
    shipped = "shipped"
    delivered = "delivered"  # fulfilled — mints an authenticity serial per piece
    cancelled = "cancelled"


class ContactMethod(enum.StrEnum):
    """How the customer wants sales to follow up."""

    call = "call"  # direct phone call
    agent = "agent"  # via a sales agent
    whatsapp = "whatsapp"


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_created_at", "created_at"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_province", "province"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reference: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)

    full_name: Mapped[str] = mapped_column(String(60), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    store_name: Mapped[str] = mapped_column(String(80), nullable=False)
    province: Mapped[str] = mapped_column(String(40), nullable=False)
    city: Mapped[str | None] = mapped_column(String(60))
    contact_method: Mapped[ContactMethod] = mapped_column(
        SAEnum(ContactMethod, name="contact_method"),
        default=ContactMethod.call,
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(String(300))  # customer's note
    internal_note: Mapped[str | None] = mapped_column(String(1000))  # admin-only

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status"),
        default=OrderStatus.new,
        nullable=False,
    )
    # Order size in GRAMS (wholesale gold is quantified by weight, not Toman).
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Proof of Delivery (WO 7.7): who delivered, when, and the evidence ---
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_assignee: Mapped[str | None] = mapped_column(String(80))
    # {photo_url?, code?, note?} — photo doubles as the signature for MVP
    delivery_proof: Mapped[dict | None] = mapped_column(JSONB)

    # Agent who placed this order on behalf of the retailer (WO 7.5). SET NULL
    # keeps the order if the agent account is ever deleted.
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    agent = relationship("User", lazy="selectin")

    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)

    # Attribution — stored on the row so sales has it even if Matomo was blocked
    utm_source: Mapped[str | None] = mapped_column(String(120))
    utm_medium: Mapped[str | None] = mapped_column(String(120))
    utm_campaign: Mapped[str | None] = mapped_column(String(120))
    referrer: Mapped[str | None] = mapped_column(String(500))
    ip_hash: Mapped[str | None] = mapped_column(String(64))

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )
    status_log: Mapped[list["OrderStatusLog"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )
    # Authenticity serials minted when the order is delivered (one per piece).
    serials = relationship("ProductSerial", back_populates="order", lazy="selectin")

    @property
    def serial_codes(self) -> list[str]:
        """Display-form codes (DGV-XXXXXXXX) for the buyer/admin views."""
        return [f"{s.code[:3]}-{s.code[3:]}" for s in self.serials]

    @property
    def agent_username(self) -> str | None:
        """Who placed the order on behalf of the retailer (admin display)."""
        return self.agent.username if self.agent else None


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL")
    )
    # name + per-unit weight COPIED at order time (weights can change; never join
    # live data). unit_price is legacy (wholesale gold is quantified by grams).
    product_name: Mapped[str] = mapped_column(String(120), nullable=False)
    unit_weight_grams: Mapped[float | None] = mapped_column(Numeric(8, 2))
    # Legacy Toman price — no longer populated; kept for old order records.
    unit_price: Mapped[float | None] = mapped_column(Numeric(12, 0))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")


class OrderStatusLog(Base):
    __tablename__ = "order_status_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[OrderStatus | None] = mapped_column(
        Enum(OrderStatus, name="order_status", create_type=False)
    )
    to_status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", create_type=False), nullable=False
    )

    order: Mapped["Order"] = relationship(back_populates="status_log")
