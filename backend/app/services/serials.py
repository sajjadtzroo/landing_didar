"""Per-item serial codes. Codes are stored canonical (uppercase, no separator,
e.g. DGVAB12CD34) and rendered DGV-AB12CD34. Uniqueness is enforced by the DB
unique index — generation inserts with ON CONFLICT DO NOTHING and only regenerates
the shortfall, so it's correct under concurrent batches and at scale."""

import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models import Product
from app.models.product_serial import ProductSerial, SerialEvent, SerialScan

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


async def _insert_unique(
    db: AsyncSession, specs: list[dict], commit: bool
) -> list[ProductSerial]:
    """Insert one row per spec, assigning a unique `code` to each. Each spec carries a
    stable `id`; ON CONFLICT DO NOTHING skips a (vanishingly rare) code collision and
    RETURNING tells us exactly which specs landed, so we only re-code the shortfall —
    correct even when specs differ (per-order line items)."""
    for s in specs:
        s.setdefault("id", uuid.uuid4())
    remaining = list(specs)
    inserted_ids: list[uuid.UUID] = []
    for _ in range(_MAX_ROUNDS):
        if not remaining:
            break
        rows = [{**s, "code": _code()} for s in remaining]
        stmt = (
            pg_insert(ProductSerial)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["code"])
            .returning(ProductSerial.id)
        )
        got = set((await db.execute(stmt)).scalars().all())
        inserted_ids.extend(got)
        remaining = [s for s in remaining if s["id"] not in got]
    if commit:
        await db.commit()
    result = await db.execute(
        select(ProductSerial)
        .where(ProductSerial.id.in_(inserted_ids))
        .order_by(ProductSerial.created_at)
    )
    return list(result.scalars().all())


async def generate(
    db: AsyncSession, product: Product, quantity: int, batch_id: uuid.UUID
) -> list[ProductSerial]:
    """Manual batch: `quantity` codes for `product`, snapshotting its spec."""
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
    return await _insert_unique(db, specs, commit=True)


async def generate_for_order(db: AsyncSession, order: Order) -> list[ProductSerial]:
    """Mint one serial per physical unit of every catalog line item in `order`
    (status=sold, linked to the order). Snapshots name/weight from the order item (the
    sold spec) and karat/image from the live product. Idempotent per order; skips custom
    items (no product). Does NOT commit — the caller's transaction owns it."""
    already = await db.scalar(
        select(func.count())
        .select_from(ProductSerial)
        .where(ProductSerial.order_id == order.id)
    )
    if already:
        return []

    pids = [it.product_id for it in order.items if it.product_id]
    products: dict = {}
    if pids:
        rows = await db.execute(select(Product).where(Product.id.in_(pids)))
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
    serials = await _insert_unique(db, specs, commit=False)
    # Passport timeline: these pieces are born sold (delivery is the sale event).
    for s in serials:
        record_event(db, s.id, "sold", {"order_id": str(order.id)})
    return serials


def record_event(
    db: AsyncSession, serial_id: uuid.UUID, type_: str, meta: dict | None = None
) -> None:
    """Append a lifecycle event (sold/revoked/restored/…). Caller owns the commit."""
    db.add(SerialEvent(serial_id=serial_id, type=type_, meta=meta))


def qr_png(code: str, base_url: str) -> bytes:
    """QR image for a piece's label — encodes the public verify deep-link."""
    import io

    import qrcode

    img = qrcode.make(
        f"{base_url}/verify?code={format_code(code)}",
        box_size=8,
        border=2,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def log_scan(db: AsyncSession, serial_id: uuid.UUID, ip_hash: str | None) -> None:
    db.add(SerialScan(serial_id=serial_id, ip_hash=ip_hash))
    await db.commit()

def csv_safe(value: object) -> object:
    """Neutralize spreadsheet formula injection in exported cells: a leading
    = + - @ makes Excel execute the cell when the admin opens our CSV."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value
