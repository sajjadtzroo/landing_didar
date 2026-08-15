"""Bulk product import (CSV, 100–1k rows) as a pollable background job.

- Upsert by SKU: new SKUs are created, existing ones updated; a blank cell means
  "leave unchanged" on update and "default" on create.
- Persian-friendly: UTF-8 BOM (Excel), Persian/Arabic digits, and Persian labels
  for category/status/booleans are all accepted.
- Bad rows are recorded ({row, error}) while good rows still land — a 1k-row
  file with 3 typos imports 997 products and reports 3 errors.
- Optionally syncs each imported SKU's photo folder from MinIO afterwards
  (reuses services/minio_import's `{sku}/` convention).

ponytail: FastAPI BackgroundTasks + the import_jobs row is the whole worker —
single process, seconds for 1k rows. Swap in a real queue if imports ever grow
past what one request-process comfortably chews.
"""

import csv
import io
import uuid
from decimal import Decimal, InvalidOperation

from loguru import logger
from sqlalchemy import select

from app.core import db as _db  # SessionLocal resolved at call time (test-patchable)
from app.domains.catalog.models import ImportJob, Product

# CSV template — header order is the documented contract.
COLUMNS = [
    "sku", "name", "slug", "description", "weight_grams", "karat",
    "ojrat_percent", "category", "supplier", "product_status",
    "warrantable", "is_active", "sort_order",
]
REQUIRED = {"sku", "name"}

TEMPLATE_ROW = [
    "NK-EXAMPLE1", "گردنبند نمونه", "example-necklace", "توضیح محصول", "12.5",
    "18", "8", "luxury", "کارگاه تهران", "sellable", "true", "true", "0",
]

_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

_CATEGORY = {
    "daily": "daily", "lux_daily": "lux_daily", "luxury": "luxury",
    "روزمره": "daily", "لوکس روزمره": "lux_daily", "لوکس": "luxury",
}
_STATUS = {
    "sellable": "sellable", "sample": "sample", "not_for_sale": "not_for_sale",
    "قابل فروش": "sellable", "نمونه": "sample", "غیرقابل فروش": "not_for_sale",
}
_BOOL = {
    "true": True, "false": False, "1": True, "0": False,
    "yes": True, "no": False, "بله": True, "خیر": False,
}


def _num(raw: str) -> Decimal:
    return Decimal(raw.translate(_FA_DIGITS).replace("٫", ".").replace(",", ""))


def parse_csv(data: bytes) -> tuple[list[dict], list[dict]]:
    """CSV bytes -> (valid row-dicts with `_row` line numbers, errors). Raises
    ValueError only for file-level problems (bad encoding / missing headers)."""
    try:
        text = data.decode("utf-8-sig")  # tolerate Excel's BOM
    except UnicodeDecodeError as e:
        raise ValueError("فایل باید با کدگذاری UTF-8 ذخیره شده باشد") from e

    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip() for h in (reader.fieldnames or [])]
    missing = REQUIRED - set(headers)
    if missing:
        raise ValueError(f"ستون‌های اجباری یافت نشد: {', '.join(sorted(missing))}")

    rows: list[dict] = []
    errors: list[dict] = []
    for lineno, raw in enumerate(reader, start=2):  # 1 = header line
        cells = {(k or "").strip(): (v or "").strip() for k, v in raw.items() if k}
        if not any(cells.values()):
            continue  # blank line
        try:
            rows.append(_parse_row(cells, lineno))
        except ValueError as e:
            errors.append({"row": lineno, "error": str(e)})
    return rows, errors


def _parse_row(cells: dict, lineno: int) -> dict:
    sku = cells.get("sku", "")
    name = cells.get("name", "")
    if not sku:
        raise ValueError("sku خالی است")
    if not name:
        raise ValueError("name خالی است")

    out: dict = {"_row": lineno, "sku": sku[:40], "name": name[:120]}

    if v := cells.get("slug"):
        out["slug"] = v[:80]
    if v := cells.get("description"):
        out["description"] = v
    if v := cells.get("supplier"):
        out["supplier"] = v[:120]

    for field, upper in (("weight_grams", None), ("ojrat_percent", 100)):
        if v := cells.get(field):
            try:
                n = _num(v)
            except InvalidOperation:
                raise ValueError(f"{field} عدد معتبر نیست: «{v}»") from None
            if n < 0 or (upper is not None and n > upper):
                raise ValueError(f"{field} خارج از بازه است: «{v}»")
            out[field] = n
    if v := cells.get("karat"):
        try:
            k = int(_num(v))
        except InvalidOperation:
            raise ValueError(f"karat عدد معتبر نیست: «{v}»") from None
        if not 1 <= k <= 24:
            raise ValueError(f"karat باید بین ۱ و ۲۴ باشد: «{v}»")
        out["karat"] = k
    if v := cells.get("sort_order"):
        try:
            out["sort_order"] = int(_num(v))
        except InvalidOperation:
            raise ValueError(f"sort_order عدد معتبر نیست: «{v}»") from None

    if v := cells.get("category"):
        if v not in _CATEGORY:
            raise ValueError(f"category نامعتبر: «{v}»")
        out["category"] = _CATEGORY[v]
    if v := cells.get("product_status"):
        if v not in _STATUS:
            raise ValueError(f"product_status نامعتبر: «{v}»")
        out["product_status"] = _STATUS[v]
    for field in ("warrantable", "is_active"):
        if v := cells.get(field):
            if v.lower() not in _BOOL:
                raise ValueError(f"{field} باید true/false باشد: «{v}»")
            out[field] = _BOOL[v.lower()]
    return out


def template_csv() -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    w.writerow(TEMPLATE_ROW)
    return buf.getvalue()


_CHUNK = 100


async def run_products_import(
    job_id: uuid.UUID, rows: list[dict], parse_errors: list[dict], sync_images: bool
) -> None:
    """The background worker. Owns its own sessions (the request is long gone);
    progress is committed per chunk so the UI poll sees it move."""
    created = updated = 0
    errors = list(parse_errors)
    touched_skus: list[str] = []
    try:
        for start in range(0, len(rows), _CHUNK):
            chunk = rows[start : start + _CHUNK]
            async with _db.SessionLocal() as db:
                skus = [r["sku"] for r in chunk]
                existing = {
                    p.sku: p
                    for p in (
                        await db.execute(select(Product).where(Product.sku.in_(skus)))
                    ).scalars()
                }
                for r in chunk:
                    data = {k: v for k, v in r.items() if k != "_row"}
                    try:
                        if r["sku"] in existing:
                            for k, v in data.items():
                                setattr(existing[r["sku"]], k, v)
                            updated += 1
                        else:
                            db.add(Product(**data))
                            created += 1
                        touched_skus.append(r["sku"])
                    except Exception as e:  # noqa: BLE001 — keep importing the rest
                        errors.append({"row": r["_row"], "error": str(e)})
                await db.commit()

                job = await db.get(ImportJob, job_id)
                job.processed = min(start + len(chunk), len(rows))
                job.created_count, job.updated_count, job.errors = created, updated, errors
                await db.commit()

        photos: dict | None = None
        if sync_images and touched_skus:
            photos = await _sync_photos(touched_skus)

        async with _db.SessionLocal() as db:
            job = await db.get(ImportJob, job_id)
            job.status = "done"
            job.processed = len(rows)
            job.created_count, job.updated_count, job.errors = created, updated, errors
            job.result = {"photos": photos} if photos else None
            await db.commit()
    except Exception as e:  # noqa: BLE001 — a failed job must say so, not vanish
        logger.exception("product import job {} failed", job_id)
        async with _db.SessionLocal() as db:
            job = await db.get(ImportJob, job_id)
            job.status = "failed"
            job.errors = [*errors, {"row": 0, "error": str(e)}]
            await db.commit()


async def _sync_photos(skus: list[str]) -> dict:
    """Pull `{sku}/` photo folders from MinIO for the touched products (reuses
    the existing importer). Missing MinIO config → reported, not fatal."""
    from app.domains.catalog.services import minio_import

    try:
        return await minio_import.import_product_images(skus=skus)
    except RuntimeError as e:  # MinIO not configured
        return {"error": str(e)}


async def run_image_sync(job_id: uuid.UUID) -> None:
    """Standalone photo-sync job (the old CLI as a button): all products."""
    try:
        result = await _sync_photos(skus=None)
        async with _db.SessionLocal() as db:
            job = await db.get(ImportJob, job_id)
            job.status = "failed" if "error" in (result or {}) else "done"
            job.result = result
            if "error" in (result or {}):
                job.errors = [{"row": 0, "error": result["error"]}]
            await db.commit()
    except Exception as e:  # noqa: BLE001
        logger.exception("image sync job {} failed", job_id)
        async with _db.SessionLocal() as db:
            job = await db.get(ImportJob, job_id)
            job.status = "failed"
            job.errors = [{"row": 0, "error": str(e)}]
            await db.commit()
