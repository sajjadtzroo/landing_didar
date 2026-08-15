import uuid
from typing import Any

from sqlalchemy import Select, func, select

from app.domains.serials.models import BuybackRequest, BuybackStatus, ProductSerial
from app.shared.cqrs import BaseQuery


class BuybackQuery(BaseQuery[BuybackRequest]):
    model = BuybackRequest

    async def latest_status(self, serial_id: uuid.UUID) -> BuybackStatus | None:
        """Latest buyback request status for a piece, if any — no price, no PII."""
        return (
            await self.db.execute(
                select(BuybackRequest.status)
                .where(BuybackRequest.serial_id == serial_id)
                .order_by(BuybackRequest.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def has_open(self, serial_id: uuid.UUID) -> bool:
        """Is there an under-review request for this piece already?"""
        row = (
            await self.db.execute(
                select(BuybackRequest.id).where(
                    BuybackRequest.serial_id == serial_id,
                    BuybackRequest.status == BuybackStatus.under_review,
                )
            )
        ).scalar_one_or_none()
        return row is not None

    def _admin_stmt(self, status: BuybackStatus | None) -> Select:
        stmt = select(BuybackRequest, ProductSerial).join(
            ProductSerial, ProductSerial.id == BuybackRequest.serial_id
        )
        if status:
            stmt = stmt.where(BuybackRequest.status == status)
        return stmt

    async def admin_page(
        self, *, status: BuybackStatus | None, page: int, page_size: int
    ) -> tuple[list[Any], int]:
        """(rows, total) — each row is (buyback, serial), newest first."""
        count = select(func.count()).select_from(BuybackRequest)
        if status:
            count = count.where(BuybackRequest.status == status)
        total = await self.db.scalar(count)
        rows = await self.db.execute(
            self._admin_stmt(status)
            .order_by(BuybackRequest.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows.all()), total or 0

    async def admin_export(self, status: BuybackStatus | None) -> list[Any]:
        rows = await self.db.execute(
            self._admin_stmt(status).order_by(BuybackRequest.created_at.desc())
        )
        return list(rows.all())
