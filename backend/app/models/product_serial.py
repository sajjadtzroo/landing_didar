import enum
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class ProductSerialStatus(enum.StrEnum):
    in_stock = "in_stock"
    sold = "sold"
    revoked = "revoked"  # misprint / stolen batch / destroyed — verifies as NOT authentic


class ProductSerial(Base):
    """A unique code for ONE physical piece (1 product model -> N pieces). The
    attesting fields (name/karat/weight/image) are SNAPSHOT at generation time so a
    certificate always describes what was actually sold, even after the product row
    is renamed or re-photographed. `code` is stored canonical (uppercase, no
    separator); the UI renders it as DGV-XXXXXXXX."""

    __tablename__ = "product_serials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    # RESTRICT: a model with issued pieces must not be silently deleted (that would
    # invalidate certificates already in customers' hands).
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=False
    )

    # --- snapshot of the product spec at generation time (the certificate) ---
    product_name: Mapped[str] = mapped_column(String(120), nullable=False)
    karat: Mapped[int | None] = mapped_column(Integer)
    weight_grams: Mapped[float | None] = mapped_column(Numeric(8, 2))
    image_url: Mapped[str | None] = mapped_column(String(500))

    status: Mapped[ProductSerialStatus] = mapped_column(
        SAEnum(ProductSerialStatus, name="product_serial_status"),
        default=ProductSerialStatus.in_stock,
        nullable=False,
    )
    # All rows from one generate call share a batch_id (recall / re-export a print run).
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    note: Mapped[str | None] = mapped_column(String(300))

    product = relationship("Product")
    scans: Mapped[list["SerialScan"]] = relationship(
        back_populates="serial", cascade="all, delete-orphan"
    )


class SerialScan(Base):
    """One row per public verification hit. Powers the copy-attack signal
    (verify_count / distinct IPs / first_verified_at) in the admin list."""

    __tablename__ = "serial_scans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    serial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_serials.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ip_hash: Mapped[str | None] = mapped_column(String(64))

    serial: Mapped["ProductSerial"] = relationship(back_populates="scans")
