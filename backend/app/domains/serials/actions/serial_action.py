"""Per-item serial minting and lifecycle writes. Codes are stored canonical
(uppercase, no separator, e.g. DGVAB12CD34) and rendered DGV-AB12CD34.
Uniqueness is enforced by the DB unique index — generation inserts with
ON CONFLICT DO NOTHING and only regenerates the shortfall, so it's correct
under concurrent batches and at scale."""

import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.domains.catalog import Product
from app.domains.orders import Order
from app.domains.serials.models import (
    ProductSerial,
    ProductSerialStatus,
    SerialEvent,
    SerialScan,
)
from app.domains.serials.schemas import SerialUpdate
from app.domains.serials.services.codes import new_code
from app.shared.cqrs import BaseAction

_MAX_ROUNDS = 10


class SerialAction(BaseAction[ProductSerial]):
    model = ProductSerial

    async def _insert_unique(
        self, specs: list[dict], commit: bool
    ) -> list[ProductSerial]:
        """Insert one row per spec, assigning a unique `code` to each. Each spec
        carries a stable `id`; ON CONFLICT DO NOTHING skips a (vanishingly rare)
        code collision and RETURNING tells us exactly which specs landed, so we
        only re-code the shortfall — correct even when specs differ (per-order
        line items)."""
        for s in specs:
            s.setdefault("id", uuid.uuid4())
        remaining = list(specs)
        inserted_ids: list[uuid.UUID] = []
        for _ in range(_MAX_ROUNDS):
            if not remaining:
                break
            rows = [{**s, "code": new_code()} for s in remaining]
            stmt = (
                pg_insert(ProductSerial)
                .values(rows)
                .on_conflict_do_nothing(index_elements=["code"])
                .returning(ProductSerial.id)
            )
            got = set((await self.db.execute(stmt)).scalars().all())
            inserted_ids.extend(got)
            remaining = [s for s in remaining if s["id"] not in got]
        if commit:
            await self.db.commit()
        result = await self.db.execute(
            select(ProductSerial)
            .where(ProductSerial.id.in_(inserted_ids))
            .order_by(ProductSerial.created_at)
        )
        return list(result.scalars().all())

    async def generate(
        self, product_id: uuid.UUID, quantity: int
    ) -> list[ProductSerial]:
        """Manual batch: `quantity` codes for the product, snapshotting its
        spec. All rows share a fresh batch_id (recall / re-export a print run)."""
        product = await self.db.get(Product, product_id)
        if product is None:
            raise HTTPException(404, detail="Product not found")
        batch_id = uuid.uuid4()
        specs = [
            {
                "product_id": product.id,
                "product_name": product.name,
                "karat": product.karat,
                "weight_grams": product.weight_grams,
                "image_url": product.image_url,
                "status": "in_stock",
                "batch_id": batch_id,
                "order_id": None,
                "note": None,
            }
            for _ in range(quantity)
        ]
        return await self._insert_unique(specs, commit=True)

    async def generate_for_order(self, order: Order) -> list[ProductSerial]:
        """Mint one serial per physical unit of every catalog line item in
        `order` (status=sold, linked to the order). Snapshots name/weight from
        the order item (the sold spec) and karat/image from the live product.
        Idempotent per order; skips custom items (no product). Does NOT commit —
        the caller's transaction owns it."""
        already = await self.db.scalar(
            select(func.count())
            .select_from(ProductSerial)
            .where(ProductSerial.order_id == order.id)
        )
        if already:
            return []

        pids = [it.product_id for it in order.items if it.product_id]
        products: dict = {}
        if pids:
            rows = await self.db.execute(select(Product).where(Product.id.in_(pids)))
            products = {p.id: p for p in rows.scalars()}

        batch_id = uuid.uuid4()
        specs: list[dict] = []
        for it in order.items:
            if not it.product_id:
                continue  # custom item — no catalog product to certify
            p = products.get(it.product_id)
            for _ in range(it.quantity):
                specs.append(
                    {
                        "product_id": it.product_id,
                        "product_name": it.product_name,
                        "karat": p.karat if p else None,
                        "weight_grams": it.unit_weight_grams,
                        "image_url": p.image_url if p else None,
                        "status": "sold",
                        "batch_id": batch_id,
                        "order_id": order.id,
                        "note": None,
                    }
                )
        if not specs:
            return []
        serials = await self._insert_unique(specs, commit=False)
        # Passport timeline: these pieces are born sold (delivery is the sale event).
        for s in serials:
            self.record_event(s.id, "sold", {"order_id": str(order.id)})
        return serials

    def record_event(
        self, serial_id: uuid.UUID, type_: str, meta: dict | None = None
    ) -> None:
        """Append a lifecycle event (sold/revoked/restored/…). Caller owns the
        commit."""
        self.db.add(SerialEvent(serial_id=serial_id, type=type_, meta=meta))

    async def log_scan(self, serial_id: uuid.UUID, ip_hash: str | None) -> None:
        """One row per public verification hit — the copy-attack signal.
        Deliberate commit inside a GET flow: the scan log must persist even
        though verify is a read."""
        self.db.add(SerialScan(serial_id=serial_id, ip_hash=ip_hash))
        await self.db.commit()

    async def update_admin(
        self, serial: ProductSerial, payload: SerialUpdate
    ) -> ProductSerial:
        """Admin PATCH (status/note) — a status transition lands on the passport
        timeline (back to in_stock reads as "restored")."""
        old_status = serial.status
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(serial, k, v)
        if serial.status != old_status:
            type_ = (
                "restored"
                if serial.status == ProductSerialStatus.in_stock
                else serial.status.value
            )
            self.record_event(serial.id, type_, {"from": old_status.value})
        return await self.commit_and_refresh(serial)
