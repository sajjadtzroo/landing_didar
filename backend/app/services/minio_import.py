"""Import product photos from a private MinIO bucket into the local media store.

Each product's photos live in a bucket folder named after its SKU (e.g. `2000/`).
For every product we list that folder, download the images into
`media_root/products/{sku}/…` (served by the existing /media StaticFiles mount)
and record the served paths on `product.images` (+ `image_url` = the first one).

MinIO is touched ONLY here, not at request time. Idempotent — re-run to re-sync.
Run: `python -m app.import_images`.
"""

import asyncio
import os
from pathlib import Path

from loguru import logger
from sqlalchemy import select

from app.core.config import settings
from app.core import db as _db  # SessionLocal resolved at call time (test-patchable)
from app.models.product import Product

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}


def _make_client():
    """Build a MinIO client from settings, or fail with a clear message."""
    from minio import Minio  # lazy import: the app doesn't need minio at runtime

    missing = [
        name
        for name in ("minio_endpoint", "minio_access_key", "minio_secret_key", "minio_bucket")
        if not getattr(settings, name)
    ]
    if missing:
        raise RuntimeError(
            "MinIO is not configured — set "
            + ", ".join(m.upper() for m in missing)
            + " in the environment."
        )
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _list_images(client, sku: str) -> list[str]:
    """Object keys under `{sku}/` with an image extension, sorted by name."""
    prefix = f"{sku}/"
    keys = [
        obj.object_name
        for obj in client.list_objects(settings.minio_bucket, prefix=prefix, recursive=True)
        if os.path.splitext(obj.object_name)[1].lower() in _IMAGE_EXTS
        and ".." not in obj.object_name  # defensive: no path traversal
    ]
    return sorted(keys)


def _download(client, key: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = client.get_object(settings.minio_bucket, key)
    try:
        dest.write_bytes(resp.read())
    finally:
        resp.close()
        resp.release_conn()


async def import_product_images(client=None, skus: list[str] | None = None) -> dict:
    """Sync products' `{sku}/` MinIO folders into local media and record the
    served paths. `skus` limits the sync (bulk-import follow-up); None = all.
    Returns {'products', 'photos', 'skipped'} for reporting."""
    client = client or _make_client()
    media_root = Path(settings.media_root)
    prefix_url = settings.media_url_prefix
    photos = 0
    skipped: list[str] = []

    async with _db.SessionLocal() as db:
        stmt = select(Product)
        if skus is not None:
            stmt = stmt.where(Product.sku.in_(skus))
        products = (await db.execute(stmt)).scalars().all()
        for p in products:
            keys = await asyncio.to_thread(_list_images, client, p.sku)
            if not keys:
                skipped.append(p.sku)
                continue
            urls: list[str] = []
            for key in keys:
                rel = key[len(f"{p.sku}/"):]  # path within the product folder
                dest = media_root / "products" / p.sku / rel
                await asyncio.to_thread(_download, client, key, dest)
                urls.append(f"{prefix_url}/products/{p.sku}/{rel}")
                photos += 1
            p.images = urls
            p.image_url = urls[0]
        await db.commit()
        total = len(products)

    logger.info(
        "minio import: {} products, {} photos, {} skipped ({})",
        total,
        photos,
        len(skipped),
        ", ".join(skipped) or "none",
    )
    return {"products": total, "photos": photos, "skipped": skipped}
