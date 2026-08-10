import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Warranty(Base):
    """One warranty per piece (WO 7.8), keyed by the UID. Status is derived
    (active while now < expires_at) — nothing to keep in sync."""

    __tablename__ = "warranties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    serial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_serials.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    customer_name: Mapped[str | None] = mapped_column(String(60))
    customer_phone: Mapped[str | None] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str | None] = mapped_column(String(300))

    serial = relationship("ProductSerial")


class BuybackStatus(enum.StrEnum):
    under_review = "under_review"
    accepted = "accepted"
    rejected = "rejected"


class BuybackRequest(Base):
    """بازخرید پایه (WO 7.9): a UID-anchored request, processed by the admin."""

    __tablename__ = "buyback_requests"
    # One OPEN request per piece — the DB backstop for the public endpoint's
    # check-then-insert (concurrent duplicates hit this, not the app check).
    __table_args__ = (
        Index(
            "uq_buyback_open_serial",
            "serial_id",
            unique=True,
            postgresql_where=text("status = 'under_review'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    serial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_serials.id", ondelete="CASCADE"), index=True, nullable=False
    )
    requester_name: Mapped[str] = mapped_column(String(60), nullable=False)
    requester_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[BuybackStatus] = mapped_column(
        SAEnum(BuybackStatus, name="buyback_status"),
        default=BuybackStatus.under_review,
        nullable=False,
    )
    # قیمت پیشنهادی اولیه — set by the admin during review (Toman)
    offered_price: Mapped[float | None] = mapped_column(Numeric(14, 0))
    admin_note: Mapped[str | None] = mapped_column(String(300))

    serial = relationship("ProductSerial")
