import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class AgentRetailer(Base):
    """Assignment: which retailers (approved customers) an agent serves (WO 7.5)."""

    __tablename__ = "agent_retailers"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True
    )


class MobileGalleryItem(Base):
    """گالری سیار (WO 7.6): one physical piece (a serial) handed to an agent.
    kind splits نمونه from قابل فروش; a partial unique index guarantees a piece
    is in at most one bag at a time. Quick-sale flips the serial to sold."""

    __tablename__ = "mobile_gallery_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    serial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_serials.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # sample | sellable
    status: Mapped[str] = mapped_column(
        String(12), default="with_agent", server_default="with_agent", nullable=False
    )  # with_agent | returned | sold
    note: Mapped[str | None] = mapped_column(String(300))

    serial = relationship("ProductSerial", lazy="selectin")


class AgentVisit(Base):
    """بازدید / یادداشت پایه — an agent's field-visit note on a retailer."""

    __tablename__ = "agent_visits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    note: Mapped[str] = mapped_column(String(500), nullable=False)
