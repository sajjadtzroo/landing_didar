from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.db import get_db
from app.models.faq import FAQ
from app.models.product import Product
from app.schemas.faq import FAQCreate, FAQOut, FAQUpdate
from app.schemas.product import AdminProductOut, ProductCreate, ProductUpdate
from app.services.storage import get_storage

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
    url = await get_storage().save(file.filename or "upload", data)
    return {"url": url}


# ---- Products ----
@router.get("/products", response_model=list[AdminProductOut])
async def list_products(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Product).order_by(Product.sort_order))
    return res.scalars().all()


@router.post("/products", response_model=AdminProductOut, status_code=201)
async def create_product(payload: ProductCreate, db: AsyncSession = Depends(get_db)):
    product = Product(**payload.model_dump())
    db.add(product)
    await db.commit()
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
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(404, detail="Product not found")
    await db.delete(product)
    await db.commit()


@router.post("/products/{product_id}/image", response_model=AdminProductOut)
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(404, detail="Product not found")
    url = await get_storage().save(file.filename or "upload", await file.read())
    product.image_url = url
    await db.commit()
    await db.refresh(product)
    return product


# ---- FAQs ----
@router.get("/faqs", response_model=list[FAQOut])
async def list_faqs(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FAQ).order_by(FAQ.sort_order))
    return res.scalars().all()


@router.post("/faqs", response_model=FAQOut, status_code=201)
async def create_faq(payload: FAQCreate, db: AsyncSession = Depends(get_db)):
    faq = FAQ(**payload.model_dump())
    db.add(faq)
    await db.commit()
    await db.refresh(faq)
    return faq


@router.patch("/faqs/{faq_id}", response_model=FAQOut)
async def update_faq(
    faq_id: str, payload: FAQUpdate, db: AsyncSession = Depends(get_db)
):
    faq = await db.get(FAQ, faq_id)
    if not faq:
        raise HTTPException(404, detail="FAQ not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(faq, k, v)
    await db.commit()
    await db.refresh(faq)
    return faq


@router.delete("/faqs/{faq_id}", status_code=204)
async def delete_faq(faq_id: str, db: AsyncSession = Depends(get_db)):
    faq = await db.get(FAQ, faq_id)
    if not faq:
        raise HTTPException(404, detail="FAQ not found")
    await db.delete(faq)
    await db.commit()
