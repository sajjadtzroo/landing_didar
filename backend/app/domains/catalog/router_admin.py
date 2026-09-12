import asyncio
import io
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.storage import get_storage, sniff_ok
from app.domains.catalog import import_service as product_import
from app.domains.catalog.models import ImportJob, Product
from app.domains.catalog.schemas import (
    AdminProductOut,
    ImportJobOut,
    ProductCreate,
    ProductUpdate,
)
from app.domains.users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])

# Generic media upload (landing hero video/poster, section images). Images are
# small; a hero video is the only heavy case — cap keeps a worker from OOMing on
# a bad upload (whole file is read into memory by Starlette).
_ALLOWED_MEDIA = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "video/mp4", "video/webm",
}
_MAX_MEDIA_BYTES = 60 * 1024 * 1024  # 60 MB


@router.post("/media")
async def upload_media(file: UploadFile = File(...)):
    if file.content_type not in _ALLOWED_MEDIA:
        raise HTTPException(415, detail="Unsupported media type")
    data = await file.read()
    if len(data) > _MAX_MEDIA_BYTES:
        raise HTTPException(413, detail="File too large (max 60MB)")
    if not sniff_ok(file.content_type, data):
        raise HTTPException(415, detail="File content does not match its type")
    url = await get_storage().save(file.filename or "upload", data)
    return {"url": url}


# ---- Bulk import (WO 7.1 at scale: 100–1k rows, background worker) ----
_MAX_CSV_BYTES = 5 * 1024 * 1024  # a 1k-row CSV is ~100KB; 5MB is generous
_MAX_ROWS = 5000


@router.get("/products/import/template")
async def import_template():
    """Downloadable CSV template (header contract + one example row)."""
    return Response(
        content=product_import.template_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=products-template.csv"},
    )


@router.post("/products/import", status_code=202)
async def import_products(
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    sync_images: bool = Form(False),
):
    """Upload a CSV → returns a job id immediately; the worker upserts by SKU in
    the background (poll GET /products/import/{job_id}). `sync_images` also pulls
    each imported SKU's `{sku}/` photo folder from MinIO afterwards."""
    data = await file.read()
    if len(data) > _MAX_CSV_BYTES:
        raise HTTPException(413, detail="File too large (max 5MB)")
    try:
        rows, parse_errors = product_import.parse_csv(data)
    except ValueError as e:
        raise HTTPException(422, detail=str(e)) from None
    if len(rows) > _MAX_ROWS:
        raise HTTPException(422, detail=f"حداکثر {_MAX_ROWS} ردیف در هر فایل")
    if not rows and not parse_errors:
        raise HTTPException(422, detail="فایل خالی است")

    job = ImportJob(kind="products_csv", status="running", total=len(rows), errors=parse_errors)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    background.add_task(
        product_import.run_products_import, job.id, rows, parse_errors, sync_images
    )
    return {"job_id": str(job.id), "total": len(rows), "parse_errors": len(parse_errors)}


@router.get("/products/import/{job_id}", response_model=ImportJobOut)
async def import_status(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await db.get(ImportJob, job_id)
    if job is None:
        raise HTTPException(404, detail="Job not found")
    return job


@router.post("/products/sync-images", status_code=202)
async def sync_images(background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Pull every product's `{sku}/` photo folder from MinIO (the old CLI as a
    button), as a pollable background job."""
    job = ImportJob(kind="image_sync", status="running")
    db.add(job)
    await db.commit()
    await db.refresh(job)
    background.add_task(product_import.run_image_sync, job.id)
    return {"job_id": str(job.id)}


# ---- Products ----
@router.get("/products", response_model=list[AdminProductOut])
async def list_products(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Product).order_by(Product.sort_order))
    return res.scalars().all()


async def _commit_or_409(db: AsyncSession) -> None:
    """Duplicate sku/slug is admin input error, not a server fault — 409 with a
    Persian message instead of an unhandled IntegrityError 500."""
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        msg = str(exc.orig)
        if "products_sku_key" in msg:
            raise HTTPException(409, detail="این کد (SKU) قبلاً ثبت شده است") from exc
        if "slug" in msg:
            raise HTTPException(409, detail="این نامک (slug) قبلاً ثبت شده است") from exc
        raise HTTPException(409, detail="مقدار تکراری — کد یا نامک را تغییر دهید") from exc


@router.post("/products", response_model=AdminProductOut, status_code=201)
async def create_product(payload: ProductCreate, db: AsyncSession = Depends(get_db)):
    product = Product(**payload.model_dump())
    db.add(product)
    await _commit_or_409(db)
    await db.refresh(product)
    return product


@router.patch("/products/{product_id}", response_model=AdminProductOut)
async def update_product(
    product_id: str, payload: ProductUpdate, db: AsyncSession = Depends(get_db)
):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(404, detail="Product not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(product, k, v)
    await _commit_or_409(db)
    await db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(404, detail="Product not found")
    await db.delete(product)
    await db.commit()


# Product gallery uploads: normalized to webp (smaller, single format on the
# storefront) and stored under products/{sku}/ so all of a product's photos
# live in one folder — same layout the MinIO {sku}/ sync job produces.
_ALLOWED_PRODUCT_IMAGE = {"image/jpeg", "image/png", "image/webp"}


def _webp_variants(data: bytes) -> tuple[bytes, bytes]:
    """Full-size webp + 640px `-sm` card variant — the storefront's card()
    helper rewrites <name>.webp to <name>-sm.webp, so both must exist."""
    from PIL import Image

    img = Image.open(io.BytesIO(data))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if img.mode in ("P", "LA") else "RGB")
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=85, method=4)
    sm = img.copy()
    sm.thumbnail((640, 640))
    buf_sm = io.BytesIO()
    sm.save(buf_sm, "WEBP", quality=80, method=4)
    return buf.getvalue(), buf_sm.getvalue()


async def _store_product_image(product: Product, file: UploadFile) -> str:
    if file.content_type not in _ALLOWED_PRODUCT_IMAGE:
        raise HTTPException(415, detail="Unsupported media type")
    data = await file.read()
    if len(data) > _MAX_MEDIA_BYTES:
        raise HTTPException(413, detail="File too large (max 60MB)")
    if not sniff_ok(file.content_type, data):
        raise HTTPException(415, detail="File content does not match its type")
    try:
        full, sm = await asyncio.to_thread(_webp_variants, data)
    except Exception:
        raise HTTPException(415, detail="Invalid or corrupt image")
    stem = f"products/{product.sku}/{uuid.uuid4().hex[:8]}"
    await get_storage().save_at(f"{stem}-sm.webp", sm, "image/webp")
    return await get_storage().save_at(f"{stem}.webp", full, "image/webp")


@router.post("/products/{product_id}/image", response_model=AdminProductOut)
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(404, detail="Product not found")
    product.image_url = await _store_product_image(product, file)
    await db.commit()
    await db.refresh(product)
    return product


@router.post("/products/{product_id}/images", response_model=AdminProductOut)
async def upload_product_images(
    product_id: str,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Append photos to the product gallery. Each file is converted to webp and
    stored under products/{sku}/; gallery order = upload/append order."""
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(404, detail="Product not found")
    # Convert/store concurrently — Pillow runs in threads, MinIO puts are I/O.
    # gather keeps result order = file order; any failure rejects the whole
    # batch before commit, so the gallery never half-updates.
    new_urls = await asyncio.gather(
        *(_store_product_image(product, f) for f in files)
    )
    urls = [*(product.images or []), *new_urls]
    product.images = urls
    product.image_url = urls[0]
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/products/{product_id}/images", response_model=AdminProductOut)
async def delete_product_image(
    product_id: str,
    url: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove one photo (by its /media URL) from the gallery. image_url follows
    the new first gallery item. Storage object is kept — same URL may be
    referenced elsewhere (landings, portfolios) and orphans are harmless."""
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(404, detail="Product not found")
    urls = [u for u in (product.images or []) if u != url]
    if len(urls) == len(product.images or []):
        # Not in the gallery — maybe it's the standalone primary image.
        if product.image_url == url:
            product.image_url = urls[0] if urls else None
            await db.commit()
            await db.refresh(product)
            return product
        raise HTTPException(404, detail="Image not on this product")
    product.images = urls
    product.image_url = urls[0] if urls else None
    await db.commit()
    await db.refresh(product)
    return product
