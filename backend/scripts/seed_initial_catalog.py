"""One-off: seed the initial Didar catalog (malachite/سیفی, سرویس تراش, پملاتو)
from the supplier spreadsheet, with galleries served straight from MinIO.

Images were uploaded to the bucket under `products/{sku}/N.jpg`, so each
product's `images` point at `/media/products/{sku}/…` which the app streams
from object storage (durable across redeploys — no local media disk needed).

Idempotent: a SKU that already exists is left untouched. Run inside the
backend container:  python scripts/seed_initial_catalog.py
"""

import asyncio
import os

from sqlalchemy import select

from app.core import db as _db
from app.core.config import settings
from app.domains.catalog.models import Product

FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}


def fa(s: str) -> str:
    return s.translate(FA)


def _defs():
    out = []
    mal = "بدون زنجیر پلاک گوشواره انگشتر رزگلد و زرد"
    for n in range(1, 19):
        if n == 16:  # empty photo folder — skipped per decision
            continue
        extra = "(با کسر سنگ)" if n == 1 else ""
        out.append(
            dict(
                sku=f"MAL-{n:02d}",
                name=f"مالاکیت سیفی {n}",
                slug=f"malachite-seyfi-{n}",
                description=f"{mal}{extra}\nوزن: {fa('12')} تا {fa('15')} گرم",
                weight_grams=13.5,
                karat=18,
                ojrat_percent=11,
                category="lux_daily",
                supplier="سیفی",
                product_status="sellable",
                is_active=True,
                sort_order=n,
            )
        )
    for n in range(1, 10):
        out.append(
            dict(
                sku=f"TRSH-{n:02d}",
                name=f"سرویس تراش {n}",
                slug=f"tarash-service-{n}",
                description=f"کسر سنگ و نگین\nوزن: {fa('18')} تا {fa('35')} گرم",
                weight_grams=26.5,
                karat=18,
                ojrat_percent=7.5,
                category="daily",
                supplier="صمیمی(فاطیما)",
                product_status="sellable",
                is_active=True,
                sort_order=100 + n,
            )
        )
    out.append(
        dict(
            sku="PMLT-01",
            name="بنگل و انگشتر پملاتو",
            slug="pomellato-bangle-ring",
            description=f"کسر سنگ و نگین معمولا زرد\nوزن: {fa('12')} تا {fa('16')} گرم",
            weight_grams=14,
            karat=18,
            ojrat_percent=12,
            category="lux_daily",
            supplier="سیفی",
            product_status="sellable",
            is_active=False,
            sort_order=200,
        )
    )
    return out


def _minio():
    from minio import Minio

    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _gallery(client, sku: str) -> list[str]:
    """Served /media paths for products/{sku}/* image objects, sorted."""
    prefix = f"products/{sku}/"
    keys = sorted(
        o.object_name
        for o in client.list_objects(
            settings.minio_bucket, prefix=prefix, recursive=True
        )
        if os.path.splitext(o.object_name)[1].lower() in _IMG_EXTS
    )
    return [f"{settings.media_url_prefix}/{k}" for k in keys]


async def main() -> None:
    client = _minio()
    created = skipped = 0
    async with _db.SessionLocal() as db:
        existing = set((await db.execute(select(Product.sku))).scalars().all())
        for d in _defs():
            if d["sku"] in existing:
                skipped += 1
                continue
            imgs = _gallery(client, d["sku"])
            p = Product(**d, images=imgs, image_url=(imgs[0] if imgs else None))
            db.add(p)
            created += 1
            print(f"+ {d['sku']} imgs={len(imgs)} active={d['is_active']}")
        await db.commit()
    print(f"\nseed done: {created} created, {skipped} skipped")


if __name__ == "__main__":
    asyncio.run(main())
