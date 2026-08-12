"""Import product photos from MinIO (one folder per SKU) into local media + DB.

Run: python -m app.import_images
Requires MINIO_* env (see .env.example). Idempotent — re-run to re-sync.
"""

import asyncio

from app.domains.catalog.minio_import import import_product_images

if __name__ == "__main__":
    s = asyncio.run(import_product_images())
    print(
        f"done: {s['products']} products, {s['photos']} photos, "
        f"skipped {len(s['skipped'])}"
        + (f" ({', '.join(s['skipped'])})" if s["skipped"] else "")
    )
