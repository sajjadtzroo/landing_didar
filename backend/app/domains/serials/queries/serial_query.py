import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import Select, func, select

from app.domains.orders import Order
from app.domains.serials.models import (
    ProductSerial,
    ProductSerialStatus,
    SerialEvent,
    SerialScan,
)
from app.domains.serials.services.codes import normalize
from app.shared.cqrs import BaseQuery

# Passport timeline: mint is derived (created_at); public transitions only.
_PUBLIC_EVENTS = ("sold", "warranty_activated", "buyback_requested")


class SerialQuery(BaseQuery[ProductSerial]):
    model = ProductSerial

    async def by_code(self, raw: str) -> ProductSerial | None:
        """Normalized exact lookup — `dgv-ab12 cd34` finds DGVAB12CD34."""
        normalized = normalize(raw)
        if not normalized:
            return None
        return await self.one_or_none(
            self.stmt().where(ProductSerial.code == normalized)
        )

    async def verifiable_by_code(self, raw: str) -> ProductSerial:
        """Public passport lookup: unknown AND revoked codes raise the SAME
        opaque 404 (a revoked code is not authentic)."""
        serial = await self.by_code(raw)
        if serial is None or serial.status == ProductSerialStatus.revoked:
            raise HTTPException(404, detail="Not found")
        return serial

    async def sold_by_code(self, raw: str) -> ProductSerial:
        """Warranty/buyback both require a genuine, SOLD piece: 404 for unknown
        or revoked (opaque), 409 for a piece still in stock."""
        serial = await self.verifiable_by_code(raw)
        if serial.status != ProductSerialStatus.sold:
            raise HTTPException(409, detail="این قطعه هنوز فروخته نشده است")
        return serial

    async def public_events(self, serial_id: uuid.UUID) -> list[SerialEvent]:
        """Stored public transitions for the passport timeline, oldest first."""
        rows = await self.db.execute(
            select(SerialEvent)
            .where(
                SerialEvent.serial_id == serial_id,
                SerialEvent.type.in_(_PUBLIC_EVENTS),
            )
            .order_by(SerialEvent.created_at)
        )
        return list(rows.scalars().all())

    # --- admin list / export -------------------------------------------------

    def _admin_filter(
        self,
        stmt: Select,
        *,
        product_id: uuid.UUID | None,
        status: ProductSerialStatus | None,
        batch_id: uuid.UUID | None,
        order_id: uuid.UUID | None,
        q: str | None,
    ) -> Select:
        if product_id:
            stmt = stmt.where(ProductSerial.product_id == product_id)
        if status:
            stmt = stmt.where(ProductSerial.status == status)
        if batch_id:
            stmt = stmt.where(ProductSerial.batch_id == batch_id)
        if order_id:
            stmt = stmt.where(ProductSerial.order_id == order_id)
        if q:
            norm = normalize(q)
            if norm:
                # Prefix match — index-friendly (unlike %q%).
                stmt = stmt.where(ProductSerial.code.like(f"{norm}%"))
        return stmt

    @staticmethod
    def _scan_agg():
        return (
            select(
                SerialScan.serial_id.label("sid"),
                func.count().label("cnt"),
                func.min(SerialScan.created_at).label("first"),
            )
            .group_by(SerialScan.serial_id)
            .subquery()
        )

    async def admin_page(
        self,
        *,
        product_id: uuid.UUID | None,
        status: ProductSerialStatus | None,
        batch_id: uuid.UUID | None,
        order_id: uuid.UUID | None,
        q: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Any], int]:
        """(rows, total) — each row is (serial, verify_count, first_verified_at,
        order_reference); the scan aggregate is the copy-attack signal."""
        agg = self._scan_agg()
        base = (
            select(ProductSerial, agg.c.cnt, agg.c.first, Order.reference)
            .outerjoin(agg, agg.c.sid == ProductSerial.id)
            .outerjoin(Order, Order.id == ProductSerial.order_id)
        )
        base = self._admin_filter(
            base,
            product_id=product_id,
            status=status,
            batch_id=batch_id,
            order_id=order_id,
            q=q,
        )
        count_stmt = self._admin_filter(
            select(ProductSerial.id),
            product_id=product_id,
            status=status,
            batch_id=batch_id,
            order_id=order_id,
            q=q,
        )
        total = await self.db.scalar(
            select(func.count()).select_from(count_stmt.subquery())
        )
        rows = await self.db.execute(
            base.order_by(ProductSerial.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows.all()), total or 0

    async def admin_export(
        self,
        *,
        product_id: uuid.UUID | None,
        status: ProductSerialStatus | None,
        batch_id: uuid.UUID | None,
        order_id: uuid.UUID | None,
        q: str | None,
    ) -> list[ProductSerial]:
        stmt = self._admin_filter(
            self.stmt(),
            product_id=product_id,
            status=status,
            batch_id=batch_id,
            order_id=order_id,
            q=q,
        )
        return await self.all(stmt.order_by(ProductSerial.created_at.desc()))
