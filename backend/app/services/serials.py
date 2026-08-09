"""Per-item serial codes. Codes are stored canonical (uppercase, no separator,
e.g. DGVAB12CD34) and rendered DGV-AB12CD34. Uniqueness is enforced by the DB
unique index — generation inserts with ON CONFLICT DO NOTHING and only regenerates
the shortfall, so it's correct under concurrent batches and at scale."""

import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.product_serial import ProductSerial, SerialScan

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous chars (0/O, 1/I/L)
_MAX_ROUNDS = 10


def _code() -> str:
    return "DGV" + "".join(secrets.choice(_ALPHABET) for _ in range(8))


def normalize(raw: str) -> str:
    """Canonicalize a hand-typed code: uppercase, drop separators/spaces.
    `dgv-ab12 cd34` -> `DGVAB12CD34`."""
    return "".join(c for c in (raw or "").upper() if c.isalnum())


def format_code(code: str) -> str:
    """Canonical -> display form (DGV-XXXXXXXX)."""
    return f"{code[:3]}-{code[3:]}" if len(code) > 3 else code


async def generate(
    db: AsyncSession, product: Product, quantity: int, batch_id: uuid.UUID
) -> list[ProductSerial]:
    """Create `quantity` unique codes for `product`, snapshotting its spec. Returns
    the created rows. Commits once."""
    inserted_ids: list[uuid.UUID] = []
    remaining = quantity
    for _ in range(_MAX_ROUNDS):
        if remaining <= 0:
            break
        codes: set[str] = set()
        while len(codes) < remaining:
            codes.add(_code())
        rows = [
            {
                "id": uuid.uuid4(),
                "code": c,
                "product_id": product.id,
                "product_name": product.name,
                "karat": product.karat,
                "weight_grams": product.weight_grams,
                "image_url": product.image_url,
                "status": "in_stock",
                "batch_id": batch_id,
            }
            for c in codes
        ]
        stmt = (
            pg_insert(ProductSerial)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["code"])
            .returning(ProductSerial.id)
        )
        got = (await db.execute(stmt)).scalars().all()
        inserted_ids.extend(got)
        remaining -= len(got)
    await db.commit()

    result = await db.execute(
        select(ProductSerial)
        .where(ProductSerial.id.in_(inserted_ids))
        .order_by(ProductSerial.created_at)
    )
    return list(result.scalars().all())


async def log_scan(db: AsyncSession, serial_id: uuid.UUID, ip_hash: str | None) -> None:
    db.add(SerialScan(serial_id=serial_id, ip_hash=ip_hash))
    await db.commit()
