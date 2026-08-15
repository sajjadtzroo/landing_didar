import uuid

from app.domains.catalog import Product
from app.domains.serials.models import ProductSerial, ProductSerialStatus, Warranty
from app.shared.cqrs import BaseQuery


class WarrantyQuery(BaseQuery[Warranty]):
    model = Warranty

    async def by_serial(self, serial_id: uuid.UUID) -> Warranty | None:
        return await self.one_or_none(
            self.stmt().where(Warranty.serial_id == serial_id)
        )

    async def passport_state(
        self, serial: ProductSerial
    ) -> tuple[Warranty | None, bool]:
        """(warranty, warranty_available) for the public passport — status only,
        no PII. `warranty_available` means the piece is sold + warrantable + not
        yet activated."""
        warranty = await self.by_serial(serial.id)
        available = False
        if warranty is None and serial.status == ProductSerialStatus.sold:
            product = await self.db.get(Product, serial.product_id)
            available = bool(product and product.warrantable)
        return warranty, available
