"""Admin catalog routes — thin HTTP layer over ProductQuery/ProductAction and
the bulk-import job machinery."""

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

from app.core.storage import get_storage, sniff_ok
from app.domains.catalog.actions import ImportJobAction, ProductAction
from app.domains.catalog.queries import ImportJobQuery, ProductQuery
from app.domains.catalog.schemas import (
    AdminProductOut,
    ImportJobOut,
    ProductCreate,
    ProductUpdate,
)
from app.domains.catalog.services import import_service as product_import
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
    file: UploadFile = File(...),
    sync_images: bool = Form(False),
    jobs: ImportJobAction = Depends(),
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

    job = await jobs.start_products_import(rows, parse_errors)
    background.add_task(
        product_import.run_products_import, job.id, rows, parse_errors, sync_images
    )
    return {"job_id": str(job.id), "total": len(rows), "parse_errors": len(parse_errors)}


@router.get("/products/import/{job_id}", response_model=ImportJobOut)
async def import_status(job_id: uuid.UUID, jobs: ImportJobQuery = Depends()):
    return await jobs.by_id_or_404(job_id, detail="Job not found")


@router.post("/products/sync-images", status_code=202)
async def sync_images(background: BackgroundTasks, jobs: ImportJobAction = Depends()):
    """Pull every product's `{sku}/` photo folder from MinIO (the old CLI as a
    button), as a pollable background job."""
    job = await jobs.start_image_sync()
    background.add_task(product_import.run_image_sync, job.id)
    return {"job_id": str(job.id)}


# ---- Products ----
@router.get("/products", response_model=list[AdminProductOut])
async def list_products(products: ProductQuery = Depends()):
    return await products.admin_list()


@router.post("/products", response_model=AdminProductOut, status_code=201)
async def create_product(payload: ProductCreate, action: ProductAction = Depends()):
    return await action.create(payload)


@router.patch("/products/{product_id}", response_model=AdminProductOut)
async def update_product(
    product_id: str,
    payload: ProductUpdate,
    products: ProductQuery = Depends(),
    action: ProductAction = Depends(),
):
    product = await products.by_id_or_404(product_id, detail="Product not found")
    return await action.update(product, payload)


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    products: ProductQuery = Depends(),
    action: ProductAction = Depends(),
):
    product = await products.by_id_or_404(product_id, detail="Product not found")
    await action.delete(product)


_ALLOWED_PRODUCT_IMAGE = {"image/jpeg", "image/png", "image/webp"}
_MAX_PRODUCT_IMAGE_BYTES = 10 * 1024 * 1024


@router.post("/products/{product_id}/image", response_model=AdminProductOut)
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    products: ProductQuery = Depends(),
    action: ProductAction = Depends(),
):
    # Same guard set as /media: an unchecked upload is stored under the API
    # origin (where the admin cookie lives) and read whole into worker RAM.
    if file.content_type not in _ALLOWED_PRODUCT_IMAGE:
        raise HTTPException(415, detail="Unsupported media type")
    product = await products.by_id_or_404(product_id, detail="Product not found")
    data = await file.read()
    if len(data) > _MAX_PRODUCT_IMAGE_BYTES:
        raise HTTPException(413, detail="File too large (max 10MB)")
    if not sniff_ok(file.content_type, data):
        raise HTTPException(415, detail="File content does not match its type")
    url = await get_storage().save(file.filename or "upload", data)
    return await action.set_image(product, url)
