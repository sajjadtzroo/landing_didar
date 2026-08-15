from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.domains.catalog import Product
from app.domains.serials.actions.serial_action import SerialAction
from app.domains.serials.models import ProductSerial, Warranty
from app.domains.serials.queries import WarrantyQuery
from app.domains.serials.schemas import WarrantyActivate
from app.shared.cqrs import BaseAction


class ActivateWarrantyAction(BaseAction[Warranty]):
    """فعال‌سازی گارانتی (WO 7.8): only for a sold, warrantable piece without an
    existing warranty. 12 months from activation."""

    model = Warranty

    async def execute(
        self, serial: ProductSerial, payload: WarrantyActivate
    ) -> Warranty:
        product = await self.db.get(Product, serial.product_id)
        if not (product and product.warrantable):
            raise HTTPException(409, detail="این محصول مشمول گارانتی نیست")
        existing = await WarrantyQuery(self.db).by_serial(serial.id)
        if existing:
            raise HTTPException(409, detail="گارانتی این قطعه قبلاً فعال شده است")

        now = datetime.now(UTC)
        warranty = Warranty(
            serial_id=serial.id,
            customer_name=payload.full_name,
            customer_phone=payload.phone,
            started_at=now,
            expires_at=now + timedelta(days=365),
        )
        self.db.add(warranty)
        SerialAction(self.db).record_event(serial.id, "warranty_activated")
        try:
            await self.db.commit()
        except IntegrityError:
            # Concurrent activation won the race on the serial_id unique constraint.
            await self.db.rollback()
            raise HTTPException(
                409, detail="گارانتی این قطعه قبلاً فعال شده است"
            ) from None
        return warranty
